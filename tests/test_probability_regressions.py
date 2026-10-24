"""Regressions for symbolic endpoints and finite probability branches."""

from pathlib import Path
import tempfile
import unittest

from mathechan import Session, evaluate, MathechanError


class ProbabilityRegressions(unittest.TestCase):
    def test_symbolic_entropy_endpoints_before_and_after_storage(self):
        s = Session()
        s.evaluate("h=Entropy[BernoulliDistribution[p]]")
        for p in (0,1):
            self.assertEqual(s.evaluate(f"h/.p->{p}").text, "0")
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory)/"entropy.json"
            s.save(path)
            loaded = Session.load(path)
            self.assertEqual(loaded.evaluate("h/.p->0").text, "0")
            self.assertEqual(loaded.evaluate("h/.p->1").text, "0")

    def test_symbolic_events_choose_the_correct_piecewise_branch(self):
        s = Session()
        s.evaluate("q=Probability[x==a,{x,FiniteDistribution[{0,1,2},{1/4,1/2,1/4}]}]")
        for point, expected in ((0,"1/4"),(1,"1/2"),(2,"1/4"),(3,"0")):
            self.assertEqual(s.evaluate(f"q/.a->{point}").text, expected)
        self.assertRaises(MathechanError, s.evaluate,
                          "Probability[a,{x,BernoulliDistribution[1/2]}]")

    def test_weighted_rational_membership_has_no_false_contradiction(self):
        for weight in (1,2):
            source = f"Mean[WeightedDistribution[{{0,1}},{{w,{weight}}}]]"
            self.assertEqual(evaluate(source+"/.w->0").text, "1")
            self.assertRaises(MathechanError, evaluate, source+"/.w->-1")
        self.assertEqual(evaluate("Assuming[w>0,Mean[WeightedDistribution[{0,1},{w,1}]]]/.w->1").text,"1/2")
        self.assertRaises(MathechanError, evaluate, "Assuming[And[x>0,x<0],x]")

    def test_ordered_event_retains_real_domain_for_parameters(self):
        source = "Probability[x>a,{x,DiscreteUniformDistribution[{0,1}]}]"
        result = evaluate(source)
        self.assertTrue(result.conditions)
        self.assertEqual(evaluate(source+"/.a->0").text,"1/2")
        self.assertRaises(MathechanError, evaluate, source+"/.a->Sqrt[-1]")

    def test_mass_zero_proved_by_assumption_skips_singular_observable(self):
        source = "Assuming[p==0,Expectation[1/x,{x,FiniteDistribution[{0,1},{p,1-p}]}]]"
        self.assertEqual(evaluate(source+"/.p->0").text,"1")


if __name__ == "__main__":
    unittest.main()
