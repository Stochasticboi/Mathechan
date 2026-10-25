"""Exact joint probabilities, local observables and persistent conditions."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sympy as sp

from mathechan import Session, MathechanError, evaluate
from mathechan.kernel import Parser, build


def value(source):
    return build(Parser(source).parse())


class JointProbabilityLanguageTests(unittest.TestCase):
    distribution = "JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{1/8,1/8,1/4,1/2}]"
    diagonal = "JointFiniteDistribution[{{0,0},{1,1}},{1-p,p}]"

    def test_joint_inspection_and_reusable_input(self):
        result = evaluate(self.distribution)
        self.assertEqual(result.kind, "distribution")
        self.assertIsNotNone(result.input)
        self.assertEqual(value(result.input), value(self.distribution))
        self.assertEqual(value(f"States[{self.distribution}]"),
                         sp.Tuple(sp.Tuple(0,0),sp.Tuple(0,1),sp.Tuple(1,0),sp.Tuple(1,1)))
        self.assertEqual(value(f"Probabilities[{self.distribution}]"),
                         sp.Tuple(sp.Rational(1,8),sp.Rational(1,8),sp.Rational(1,4),sp.Rational(1,2)))

    def test_marginals_aggregate_projection_and_preserve_coordinate_order(self):
        for index, probabilities in ((1,sp.Tuple(sp.Rational(1,4),sp.Rational(3,4))),
                                     (2,sp.Tuple(sp.Rational(3,8),sp.Rational(5,8)))):
            with self.subTest(index=index):
                marginal = f"MarginalDistribution[{self.distribution},{index}]"
                self.assertEqual(value(f"States[{marginal}]"), sp.Tuple(0,1))
                self.assertEqual(value(f"Probabilities[{marginal}]"), probabilities)
                self.assertEqual(value(f"Expectation[1,{{x,{marginal}}}]"), 1)
        reversed_distribution = f"MarginalDistribution[{self.distribution},{{2,1}}]"
        self.assertEqual(value(f"Expectation[x,{{{{x,y}},{reversed_distribution}}}]"), sp.Rational(5,8))
        self.assertEqual(value(f"Expectation[y,{{{{x,y}},{reversed_distribution}}}]"), sp.Rational(3,4))

    def test_multivariable_probability_and_expectation_against_known_table(self):
        for observable, expected in (("x",sp.Rational(3,4)),("y",sp.Rational(5,8)),
                                     ("x*y",sp.Rational(1,2)),("1",sp.S.One)):
            with self.subTest(observable=observable):
                self.assertEqual(value(f"Expectation[{observable},{{{{x,y}},{self.distribution}}}]"), expected)
        self.assertEqual(value(f"Probability[x==y,{{{{x,y}},{self.distribution}}}]"), sp.Rational(5,8))
        self.assertEqual(value(f"Probability[And[x==1,y==1],{{{{x,y}},{self.distribution}}}]"), sp.Rational(1,2))

    def test_joint_entropy_against_four_state_formula(self):
        entropy = value(f"Entropy[{self.distribution}]")
        self.assertEqual(sp.simplify(entropy-sp.Rational(7,4)*sp.log(2)),0)

    def test_conditioning_and_marginal_agree_with_bayes(self):
        conditional = f"ConditionalDistribution[y==1,{{{{x,y}},{self.distribution}}}]"
        self.assertEqual(value(f"Expectation[1,{{{{x,y}},{conditional}}}]"),1)
        self.assertEqual(value(f"Expectation[x,{{{{x,y}},{conditional}}}]"),sp.Rational(4,5))
        self.assertEqual(value(f"Probability[y==1,{{{{x,y}},{conditional}}}]"),1)
        marginal = f"MarginalDistribution[{conditional},1]"
        self.assertEqual(value(f"Mean[{marginal}]"),sp.Rational(4,5))

    def test_conditional_distribution_also_accepts_univariate_input(self):
        conditional = "ConditionalDistribution[x>=1,{x,FiniteDistribution[{0,1,2},{1/4,1/2,1/4}]}]"
        self.assertEqual(value(f"Mean[{conditional}]"),sp.Rational(4,3))
        self.assertEqual(value(f"Expectation[1,{{x,{conditional}}}]"),1)

    def test_covariance_and_correlation_for_real_observables(self):
        self.assertEqual(value(f"Covariance[x,y,{{{{x,y}},{self.distribution}}}]"),sp.Rational(1,32))
        correlation = value(f"Correlation[x,y,{{{{x,y}},{self.distribution}}}]" )
        self.assertEqual(sp.simplify(correlation-1/sp.sqrt(45)),0)
        self.assertEqual(value(f"Covariance[x,x,{{{{x,y}},{self.distribution}}}]"),sp.Rational(3,16))
        self.assertEqual(value(f"Correlation[x,x,{{{{x,y}},{self.distribution}}}]"),1)
        self.assertEqual(value(f"Covariance[1,y,{{{{x,y}},{self.distribution}}}]"),0)

    def test_correlation_rejects_constant_and_complex_observables(self):
        for operation in ("Correlation[1,y", "Covariance[Sqrt[-1]*x,y"):
            with self.subTest(operation=operation), self.assertRaises(MathechanError):
                evaluate(f"{operation},{{{{x,y}},{self.distribution}}}]")

    def test_joint_binders_shadow_definitions_without_session_leak(self):
        session = Session()
        session.evaluate("x=99")
        session.evaluate("y=100")
        session.evaluate(f"d={self.distribution}")
        self.assertEqual(session.evaluate("Expectation[x+y,{{x,y},d}]").text,"11/8")
        self.assertEqual(session.evaluate("Probability[x==1,{{x,y},d}]").text,"3/4")
        self.assertEqual(session.evaluate("x").text,"99")
        self.assertEqual(session.evaluate("y").text,"100")

    def test_zero_mass_rows_are_skipped_before_observable_or_event(self):
        distribution = "JointFiniteDistribution[{{0,0},{1,1}},{0,1}]"
        self.assertEqual(value(f"Expectation[1/x,{{{{x,y}},{distribution}}}]"),1)
        self.assertEqual(value(f"Probability[1/x>0,{{{{x,y}},{distribution}}}]"),1)
        self.assertEqual(value(f"Support[{distribution}]"),sp.Tuple(sp.Tuple(1,1)))
        conditional = f"ConditionalDistribution[1/x>0,{{{{x,y}},{distribution}}}]"
        self.assertEqual(value(f"Expectation[x,{{{{x,y}},{conditional}}}]"),1)

    def test_deferred_joint_observable_uses_actual_parameter(self):
        session = Session()
        session.evaluate(f"DefineDelayed[f,{{p}},Expectation[x*y,{{{{x,y}},{self.diagonal}}}]]")
        self.assertEqual(session.evaluate("f[1/4]").text,"1/4")
        self.assertEqual(session.evaluate("f[0]").text,"0")
        self.assertRaises(MathechanError,session.evaluate,"f[-1]")
        self.assertRaises(MathechanError,session.evaluate,"f[2]")

    def test_zero_probability_condition_and_undecided_event_are_controlled(self):
        for event in ("False","x==3","x==a"):
            with self.subTest(event=event), self.assertRaises(MathechanError):
                evaluate(f"ConditionalDistribution[{event},{{{{x,y}},{self.distribution}}}]")

    def test_conditional_requirements_survive_constant_result_and_storage(self):
        source = f"ConditionalDistribution[x==1,{{{{x,y}},{self.diagonal}}}]"
        session = Session()
        self.assertTrue(session.evaluate("d="+source).conditions)
        self.assertEqual(session.evaluate("Expectation[x,{{x,y},d}]/.p->1/2").text,"1")
        self.assertRaises(MathechanError,session.evaluate,"Expectation[x,{{x,y},d}]/.p->0")
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory)/"conditional.json"
            session.save(path)
            with patch("mathechan.kernel.build",side_effect=AssertionError("source executed on load")):
                loaded = Session.load(path)
            self.assertEqual(loaded.evaluate("Expectation[1,{{x,y},d}]/.p->1").text,"1")
            self.assertRaises(MathechanError,loaded.evaluate,"Expectation[1,{{x,y},d}]/.p->0")

    def test_correlation_variance_requirements_survive_parameter_replacement(self):
        source = f"Correlation[x,y,{{{{x,y}},{self.diagonal}}}]"
        result = evaluate(source)
        self.assertTrue(result.conditions)
        self.assertEqual(evaluate(source+"/.p->1/2").text,"1")
        for p in (0,1):
            with self.subTest(p=p),self.assertRaises(MathechanError):
                evaluate(source+f"/.p->{p}")

    def test_invalid_joint_shapes_binders_and_indices_are_controlled(self):
        sources = (
            "JointFiniteDistribution[{{0,0},{0,0}},{1/2,1/2}]",
            "JointFiniteDistribution[{{0,0},{1}},{1/2,1/2}]",
            "JointFiniteDistribution[{{0,0},{1,1}},{1/4,1/4}]",
            "JointFiniteDistribution[{{0,Sqrt[-1]}},{1}]",
            f"MarginalDistribution[{self.distribution},0]",
            f"MarginalDistribution[{self.distribution},3]",
            f"MarginalDistribution[{self.distribution},{{1,1}}]",
            f"Expectation[x,{{{{x,x}},{self.distribution}}}]",
            f"Expectation[x,{{x,{self.distribution}}}]",
            f"Probability[x==1,{{{{x,y,z}},{self.distribution}}}]",
        )
        for source in sources:
            with self.subTest(source=source),self.assertRaises(MathechanError):
                evaluate(source)

    def test_new_probability_names_are_protected(self):
        for name in ("JointFiniteDistribution","MarginalDistribution","ConditionalDistribution",
                     "Covariance","Correlation"):
            with self.subTest(name=name),self.assertRaises(MathechanError):
                Session().evaluate(name+"=1")


if __name__ == "__main__":
    unittest.main()
