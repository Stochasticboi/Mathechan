"""Finite probability syntax, exact identities and persistent domain contracts."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sympy as sp

from mathechan import MathechanError, Session, evaluate
from mathechan.kernel import Parser, build


def value(source):
    return build(Parser(source).parse())


class ProbabilityLanguageTests(unittest.TestCase):
    distribution = "FiniteDistribution[{0,1,2},{1/4,1/2,1/4}]"

    def test_support_and_probabilities_preserve_exact_entries(self):
        self.assertEqual(value(f"Support[{self.distribution}]"), sp.Tuple(0,1,2))
        self.assertEqual(value(f"Probabilities[{self.distribution}]"),
                         sp.Tuple(sp.Rational(1,4),sp.Rational(1,2),sp.Rational(1,4)))

    def test_exact_moments_against_finite_three_state_reference(self):
        self.assertEqual(value(f"Mean[{self.distribution}]"), 1)
        self.assertEqual(value(f"Variance[{self.distribution}]"), sp.Rational(1,2))
        self.assertEqual(value(f"StandardDeviation[{self.distribution}]"), sp.sqrt(sp.Rational(1,2)))
        self.assertEqual(value(f"Expectation[x^2,{{x,{self.distribution}}}]"), sp.Rational(3,2))
        self.assertEqual(value(f"Expectation[1,{{x,{self.distribution}}}]"), 1)

    def test_entropy_is_in_nats_with_zero_mass_convention(self):
        entropy = value(f"Entropy[{self.distribution}]")
        self.assertEqual(sp.simplify(entropy-sp.Rational(3,2)*sp.log(2)), 0)
        self.assertEqual(value("Entropy[FiniteDistribution[{0,1},{0,1}]]"), 0)
        self.assertEqual(value("Entropy[FiniteDistribution[{0,1},{1,0}]]"), 0)

    def test_effective_support_omits_exactly_zero_mass(self):
        self.assertEqual(value("Support[FiniteDistribution[{0,1},{0,1}]]"), sp.Tuple(1))
        self.assertEqual(value("Probabilities[FiniteDistribution[{0,1},{0,1}]]"), sp.Tuple(0,1))

    def test_observables_and_events_skip_known_zero_mass_before_evaluation(self):
        distribution = "FiniteDistribution[{0,1},{0,1}]"
        self.assertEqual(value(f"Expectation[1/x,{{x,{distribution}}}]"), 1)
        self.assertEqual(value(f"Probability[1/x>0,{{x,{distribution}}}]"), 1)
        self.assertRaises(MathechanError, evaluate,
                          "Expectation[1/x,{x,FiniteDistribution[{0,1},{p,1-p}]}]")

    def test_event_probabilities_and_complements(self):
        self.assertEqual(value(f"Probability[x==1,{{x,{self.distribution}}}]"), sp.Rational(1,2))
        self.assertEqual(value(f"Probability[And[x>=1,x<3],{{x,{self.distribution}}}]"), sp.Rational(3,4))
        self.assertEqual(value(f"Probability[Not[x==1],{{x,{self.distribution}}}]"), sp.Rational(1,2))
        self.assertEqual(value(f"Probability[True,{{x,{self.distribution}}}]"), 1)
        self.assertEqual(value(f"Probability[False,{{x,{self.distribution}}}]"), 0)

    def test_bound_variable_shadows_session_value(self):
        session = Session()
        session.evaluate("x=100")
        session.evaluate(f"d={self.distribution}")
        self.assertEqual(session.evaluate("Expectation[x,{x,d}]").text, "1")
        self.assertEqual(session.evaluate("Probability[x==1,{x,d}]").text, "1/2")
        self.assertEqual(session.evaluate("x").text, "100")

    def test_symbolic_probabilities_remain_executable_requirements(self):
        source = "Expectation[1,{x,FiniteDistribution[{0,1},{1-p,p}]}]"
        result = evaluate(source)
        self.assertEqual(result.text, "1")
        self.assertEqual(result.status, "conditional")
        self.assertTrue(result.conditions)
        for replacement in ("p->-1", "p->2", "p->Sqrt[-1]"):
            with self.subTest(replacement=replacement), self.assertRaises(MathechanError):
                evaluate(f"{source}/.{replacement}")
        self.assertEqual(evaluate(f"{source}/.p->0").text, "1")
        self.assertEqual(evaluate(f"{source}/.p->1").text, "1")

    def test_symbolic_normalization_is_not_silently_dropped(self):
        source = "Mean[FiniteDistribution[{0,1},{p,q}]]"
        self.assertTrue(evaluate(source).conditions)
        self.assertEqual(evaluate(f"{source}/.{{p->1/4,q->3/4}}").text, "3/4")
        self.assertRaises(MathechanError, evaluate, f"{source}/.{{p->1,q->1}}")

    def test_weighted_distribution_normalizes_explicitly_and_keeps_original_domain(self):
        self.assertEqual(value("Probabilities[WeightedDistribution[{0,1},{2,6}]]"),
                         sp.Tuple(sp.Rational(1,4),sp.Rational(3,4)))
        self.assertRaises(MathechanError, evaluate, "FiniteDistribution[{0,1},{2,6}]")
        source = "Expectation[1,{x,WeightedDistribution[{0,1},{a,a}]}]"
        self.assertEqual(evaluate(source).text, "1")
        self.assertTrue(evaluate(source).conditions)
        for replacement in ("a->0", "a->-1", "a->Sqrt[-1]"):
            with self.subTest(replacement=replacement), self.assertRaises(MathechanError):
                evaluate(f"{source}/.{replacement}")
        self.assertEqual(evaluate(f"{source}/.a->2").text, "1")

    def test_failed_distribution_assignment_is_atomic(self):
        session = Session()
        session.evaluate("d=FiniteDistribution[{0,1},{1/4,3/4}]")
        self.assertRaises(MathechanError, session.evaluate, "d=FiniteDistribution[{0,1},{1/4,1/4}]")
        self.assertEqual(session.evaluate("Mean[d]").text, "3/4")

    def test_deferred_function_validates_actual_probability(self):
        session = Session()
        session.evaluate("DefineDelayed[f,{p},Mean[FiniteDistribution[{0,1},{1-p,p}]]]")
        self.assertEqual(session.evaluate("f[1/4]").text, "1/4")
        self.assertEqual(session.evaluate("f[0]").text, "0")
        self.assertEqual(session.evaluate("f[1]").text, "1")
        self.assertRaises(MathechanError, session.evaluate, "f[-1]")
        self.assertRaises(MathechanError, session.evaluate, "f[2]")

    def test_distribution_and_requirement_roundtrip_without_execution(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory)/"probability.json"
            session = Session()
            session.evaluate("d=FiniteDistribution[{0,1},{1-p,p}]")
            session.evaluate("h=Hold[Expectation[x,{x,FiniteDistribution[{0,1},{1/4,3/4}]}]]")
            session.save(path)
            with patch("mathechan.kernel.build", side_effect=AssertionError("source executed on load")):
                restored = Session.load(path)
            self.assertTrue(restored.evaluate("Mean[d]").conditions)
            self.assertEqual(restored.evaluate("Mean[d]/.p->1/4").text, "1/4")
            self.assertRaises(MathechanError, restored.evaluate, "Mean[d]/.p->2")
            self.assertEqual(restored.evaluate("ReleaseHold[h]").text, "3/4")

    def test_invalid_distributions_events_and_shapes_are_controlled(self):
        sources = (
            "FiniteDistribution[{},{}]", "FiniteDistribution[{0,1},{1}]",
            "FiniteDistribution[{0,0},{1/2,1/2}]", "FiniteDistribution[{0,1},{-1,2}]",
            "FiniteDistribution[{0,1},{Sqrt[-1],1-Sqrt[-1]}]",
            "FiniteDistribution[{0,Sqrt[-1]},{1/2,1/2}]",
            "WeightedDistribution[{0,1},{0,0}]", "WeightedDistribution[{0,1},{-1,2}]",
            "Mean[{1/2,1/2}]", "Probability[x,{x,FiniteDistribution[{0,1},{1/2,1/2}]}]",
            "Expectation[x,{x}]", "Probability[x==0,{1,FiniteDistribution[{0},{1}]}]",
        )
        for source in sources:
            with self.subTest(source=source), self.assertRaises(MathechanError):
                evaluate(source)

    def test_public_probability_names_are_protected(self):
        for name in ("FiniteDistribution", "WeightedDistribution", "Probability", "Expectation",
                     "Mean", "Variance", "StandardDeviation", "Entropy", "Support", "Probabilities"):
            with self.subTest(name=name), self.assertRaises(MathechanError):
                Session().evaluate(name+"=1")


if __name__ == "__main__":
    unittest.main()
