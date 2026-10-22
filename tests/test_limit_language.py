"""Real-axis limit semantics, scopes, exclusions and structured diagnostics."""

import json
import unittest

from mathechan import MathechanError, Session, evaluate


class LimitLanguageTests(unittest.TestCase):
    def test_removable_singularities_are_limits_not_substitution(self):
        for source, expected in (("Limit[Sin[x]/x,x,0]", "1"),
                                 ("Limit[(x^2-1)/(x-1),x,1]", "2"),
                                 ("Limit[(1-Cos[x])/x^2,x,0]", "1/2")):
            with self.subTest(source=source):
                result = evaluate(source)
                self.assertEqual(result.text, expected)
                self.assertEqual(result.status, "evaluated")
                self.assertTrue(result.exact)
                self.assertFalse(any("x" in c for c in result.conditions))
                self.assertTrue(result.details["limit_expression_exclusions"])
                json.dumps(result.to_dict(), allow_nan=False)

    def test_bilateral_is_not_sympy_default_right_limit(self):
        result = evaluate("Limit[1/x,x,0]")
        self.assertEqual(result.status, "no_limit")
        self.assertIn("Limit", result.text)
        self.assertIsNone(result.input)
        for direction in ("Left", "Right"):
            with self.subTest(direction=direction):
                side = evaluate(f"Limit[1/x,x,0,{direction}]")
                self.assertEqual(side.status, "divergent")
                self.assertIn("Limit", side.text)
                self.assertTrue(side.warnings)

    def test_cusp_and_complex_principal_branch(self):
        self.assertEqual(evaluate("Limit[Sqrt[x^2]/x,x,0,Right]").text, "1")
        self.assertEqual(evaluate("Limit[Sqrt[x^2]/x,x,0,Left]").text, "-1")
        self.assertEqual(evaluate("Limit[Sqrt[x^2]/x,x,0]").status, "no_limit")
        branch = evaluate("Limit[Log[x],x,-1,Left]")
        self.assertIn("I*pi", branch.text)

    def test_infinities_and_oscillation_are_explicit(self):
        self.assertEqual(evaluate("Limit[1/x,x,Infinity]").text, "0")
        self.assertEqual(evaluate("Limit[1/x,x,-Infinity]").text, "0")
        self.assertEqual(evaluate("Limit[x^2,x,Infinity]").status, "divergent")
        self.assertEqual(evaluate("Limit[Sin[1/x],x,0]").status, "no_limit")
        self.assertEqual(evaluate("Limit[1/x^2,x,0]").status, "divergent")

    def test_variable_is_bound_but_point_and_parameters_use_session(self):
        session = Session()
        session.evaluate("x=9")
        session.evaluate("a=2")
        self.assertEqual(session.evaluate("Limit[Sin[x]/x,x,0]").text, "1")
        self.assertEqual(session.evaluate("Limit[a*x,x,a]").text, "4")
        self.assertEqual(session.evaluate("x").text, "9")
        self.assertEqual(evaluate("With[{x},{9},Limit[Sin[x]/x,x,0]]").text, "1")

    def test_original_parameter_exclusions_survive_cancellation(self):
        result = evaluate("Limit[a*x/(a*x),x,0]")
        # The bound expression simplifies, but a=0 is never a valid original input.
        self.assertIn("(a) != 0", result.conditions)
        self.assertEqual(result.status, "conditional")
        self.assertRaises(MathechanError, evaluate,
                          "Substitute[Limit[a*x/(a*x),x,0],a,0]")
        self.assertRaises(MathechanError, evaluate,
                          "Substitute[Limit[a*x/a,x,0],a,0]")

    def test_hypotheses_must_cover_the_approach(self):
        self.assertEqual(evaluate("Assuming[x>0,Limit[Sqrt[x^2]/x,x,0,Right]]").text, "1")
        for source in ("Assuming[x>0,Limit[Sqrt[x^2]/x,x,0]]",
                       "Assuming[x>0,Limit[Sqrt[x^2]/x,x,0,Left]]",
                       "Assuming[x>1,Limit[x,x,0,Right]]",
                       "Assuming[Element[x,Integers],Limit[x,x,0]]"):
            with self.subTest(source=source), self.assertRaises(MathechanError):
                evaluate(source)
        self.assertEqual(evaluate("Assuming[x>0,Limit[1/x,x,Infinity]]").text, "0")
        self.assertEqual(evaluate("Assuming[Element[x,Reals],Limit[Sin[x]/x,x,0]]").text, "1")
        self.assertEqual(evaluate("Assuming[And[x>0,a>0],Limit[x,x,0,Right]]").text, "0")

    def test_denominator_cannot_degenerate_to_zero_everywhere(self):
        for denominator in ("a*x+b", "a*x^2+b*x"):
            source = f"Limit[({denominator})/({denominator}),x,0]"
            result = evaluate(source)
            self.assertEqual(result.status, "conditional")
            self.assertTrue(result.conditions)
            self.assertRaises(MathechanError, evaluate,
                              f"Substitute[Substitute[{source},a,0],b,0]")
            self.assertEqual(evaluate(f"Substitute[Substitute[{source},a,0],b,2]").text, "1")
        self.assertRaises(MathechanError, evaluate,
                          "Limit[Sin[a*x]/Sin[a*x],x,0]")
        self.assertRaises(MathechanError, evaluate,
                          "Limit[(a*x+b)^1000/(a*x+b)^1000,x,0]")

    def test_direction_is_a_local_literal_not_a_session_binding(self):
        session = Session()
        session.evaluate("Right=7")
        self.assertEqual(session.evaluate("Limit[x,x,0,Right]").text, "0")
        self.assertEqual(session.evaluate("Right").text, "7")
        self.assertRaises(MathechanError, session.evaluate, "Limit=3")

    def test_invalid_signature_and_domain_are_rejected(self):
        for source in ("Limit[x,x]", "Limit[x,x,0,Up]", "Limit[x,x,0,1]",
                       "Limit[x,x,0,{Right}]", "Limit[x,x+1,0]", "Limit[x,Pi,0]",
                       "Limit[x,x,x]", "Limit[x,x,I]", "Limit[{x},x,0]",
                       "Limit[x==0,x,0]", "Limit[x,x,Infinity,Right]"):
            with self.subTest(source=source), self.assertRaises(MathechanError):
                evaluate(source)

    def test_pending_result_is_json_safe_and_not_numerically_certified(self):
        result = evaluate("Limit[x^a,x,0,Right]")
        self.assertEqual(result.status, "unresolved")
        self.assertIn("Limit", result.text)
        self.assertNotEqual(result.details.get("verification"), "verified")
        json.dumps(result.to_dict(), allow_nan=False)


if __name__ == "__main__":
    unittest.main()
