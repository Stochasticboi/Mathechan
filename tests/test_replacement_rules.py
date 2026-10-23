"""Rule syntax, one-pass replacement, provenance and inert persistence."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mathechan import MathechanError, Session, evaluate


class RuleTests(unittest.TestCase):
    def test_infix_and_function_forms(self):
        for source in ("x^2+a*x /. x->2", "ReplaceAll[x^2+a*x,Rule[x,2]]",
                       "Substitute[x^2+a*x,{x->2}]"):
            self.assertEqual(evaluate(source).text, "2*a + 4")
        self.assertEqual(evaluate("Substitute[x^2+a*x,x,2]").text, "2*a + 4")

    def test_first_match_simultaneous_and_sequential(self):
        self.assertEqual(evaluate("{x,y}/.{x->y,y->2}").text, "{y,2}")
        self.assertEqual(evaluate("x/.x->y/.y->2").text, "2")
        self.assertEqual(evaluate("x/.{x->1,x->2}").text, "1")
        self.assertEqual(evaluate("x/.{}").text, "x")

    def test_rule_precedence(self):
        self.assertEqual(evaluate("x+1/.x->2+3").text, "6")
        self.assertEqual(evaluate("x==y/.{x->2,y->3}").text, "(2)==(3)")
        self.assertEqual(evaluate("(x/.x->2)^3").text, "8")

    def test_larger_exact_parts_and_patterns(self):
        self.assertEqual(evaluate("Sin[x]+1/.Sin[x]->a").text, "a + 1")
        self.assertEqual(evaluate("Sin[x]+Sin[y]/.Sin[t_]->t^2").text, "x**2 + y**2")
        self.assertEqual(evaluate("{2,1/2,z}/.t_Integer:>t+1").text, "{3,(1/2),z}")
        self.assertEqual(evaluate("{N[1/2,20],1/2}/.t_Real->0").text, "{0,(1/2)}")
        self.assertEqual(evaluate("z/.t_Scalar->t^2").text, "z**2")

    def test_immediate_and_delayed_rule_objects(self):
        session = Session()
        for source in ("a=2", "r=x->a", "d=x:>a", "a=7"):
            session.evaluate(source)
        self.assertEqual(session.evaluate("x/.r").text, "2")
        self.assertEqual(session.evaluate("x/.d").text, "7")
        session.evaluate("rules={x->2,y->3}")
        self.assertEqual(session.evaluate("x+y/.rules").text, "5")

    def test_original_exclusions_are_transformed_even_after_cancellation(self):
        for source in ("x/x/.x->0", "Cancel[(x^2-1)/(x-1)]/.x->1",
                       "Substitute[x/x,{x->0}]", "Assuming[x>0,Sqrt[x^2]/.x->-1]"):
            with self.subTest(source=source), self.assertRaises(MathechanError):
                evaluate(source)
        result = evaluate("Sin[x]/.Sin[t_]->1/t")
        self.assertTrue(result.conditions)
        self.assertRaises(MathechanError, evaluate, "Substitute[Sin[x]/.Sin[t_]->1/t,x,0]")

    def test_persistent_assumptions_and_pattern_local_scope(self):
        session = Session()
        session.evaluate("Assume[x>0]")
        self.assertRaises(MathechanError, session.evaluate, "Sqrt[x^2]/.x->-1")
        # Pattern parameters do not inherit a coincident global symbol's sign.
        self.assertEqual(evaluate("Assuming[t>0,Sin[z]/.Sin[t_]->Sqrt[t^2]]").text, "sqrt(z**2)")

    def test_rule_persistence_does_not_execute_delayed_body(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory)/"session.json"
            s = Session()
            s.evaluate("r=Sin[t_]->t^2")
            s.evaluate("d=x:>Integrate[x,x]")
            s.save(path)
            with patch("mathechan.calculus.sp.integrate", side_effect=AssertionError("executed")):
                restored = Session.load(path)
            self.assertEqual(restored.evaluate("Sin[z]/.r").text, "z**2")
            self.assertEqual(restored.evaluate("x/.d").text, "x**2/2")

    def test_invalid_forms_are_controlled(self):
        for source in ("x/.2", "x/.{x->2,3}", "x/.x->", "x_", "x/.x__->2",
                       "x/.x_Unknown->2", "Rule[x]", "ReplaceAll[x]",
                       "Sin[x]/.Sin[Pi_]->Pi", "Sin[x]/.Sin[Cos_]->Cos",
                       "Sin[x]/.Sin[t_]->1/0"):
            with self.subTest(source=source), self.assertRaises(MathechanError):
                evaluate(source)

    def test_serializable_results_and_no_false_repeated_replacement(self):
        result = evaluate("x/.x->x+1")
        self.assertEqual(result.text, "x + 1")
        json.dumps(result.to_dict(), allow_nan=False)
        self.assertRaises(MathechanError, evaluate, "x//.x->x+1")
        self.assertRaises(MathechanError, evaluate,
                          "(Sum[1,{i,1,1000}]/.x->Sum[1,{j,1,1000}])+Sum[1,{k,1,1000}]")


if __name__ == "__main__":
    unittest.main()
