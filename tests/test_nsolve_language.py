"""Numerical solutions retain exact exclusions, scope and honest diagnostics."""

import json
import unittest
from decimal import Decimal, localcontext

from mathechan import MathechanError, Session, evaluate
from mathechan.kernel import Parser, build


class NumericalSolveLanguageTests(unittest.TestCase):
    def test_numeric_roots_have_precision_and_residual_metadata(self):
        result = evaluate("NSolve[x^2==2,x,50]")
        self.assertEqual(result.kind, "solutions")
        self.assertFalse(result.exact)
        self.assertEqual(result.status, "approximate")
        self.assertIsNone(result.input)
        self.assertEqual(result.details["requested_significant_digits"], 50)
        roots = list(build(Parser("NSolve[x^2==2,x,50]").parse()))
        positive = max(Decimal(str(item)) for item in roots)
        with localcontext() as context:
            context.prec = 60
            self.assertLess(abs(positive-Decimal(2).sqrt()), Decimal("1e-48"))
        json.dumps(result.to_dict(), allow_nan=False)

    def test_real_and_complex_domains_are_distinct(self):
        real = evaluate("NSolve[x^2==-1,x,Reals]")
        self.assertEqual(real.status, "no_solution")
        self.assertIn("I", evaluate("NSolve[x^2==-1,x,Complexes,40]").text)

    def test_cancellation_never_reintroduces_excluded_roots(self):
        result = evaluate("NSolve[(x^2-1)/(x-1)==0,x]")
        self.assertIn("-1.0", result.text)
        self.assertTrue(result.conditions)
        result = evaluate("NSolve[(x^2-1)/(x-1)==2,x]")
        self.assertEqual(result.status, "no_solution")

    def test_session_parameters_and_held_solution_variable(self):
        session = Session()
        session.evaluate("x=9")
        session.evaluate("a=2")
        result = session.evaluate("NSolve[x^2==a,x,Reals,40]")
        self.assertEqual(result.kind, "solutions")
        self.assertEqual(session.evaluate("x").text, "9")
        self.assertRaises(MathechanError, session.evaluate, "NSolve=3")

    def test_active_assumptions_filter_exact_roots_before_rounding(self):
        result = evaluate("Assuming[x>0,NSolve[x^2==2,x,30]]")
        self.assertNotIn("-1.414", result.text)
        self.assertTrue(result.conditions)
        session = Session()
        session.evaluate("Assume[x>0]")
        result = session.evaluate("NSolve[x^2==2,x]")
        self.assertNotIn("-1.414", result.text)

    def test_repeated_roots_do_not_require_random_initial_guesses(self):
        result = evaluate("NSolve[(x-1)^8==0,x,40]")
        self.assertIn("1.0", result.text)
        self.assertEqual(result.kind, "solutions")
        self.assertNotEqual(result.status, "unresolved")

    def test_order_hypotheses_exclude_complex_candidates_without_aborting(self):
        result = evaluate("Assuming[x>0,NSolve[x^4==1,x]]")
        self.assertIn("1.0", result.text)
        self.assertNotIn("I", result.text)
        self.assertNotIn("-1.0", result.text)
        result = evaluate("Assuming[x^2<0,NSolve[x^2==-1,x]]")
        self.assertIn("I", result.text)

    def test_rounding_into_an_excluded_boundary_is_not_verified(self):
        result = evaluate("Assuming[x<1,NSolve[10^30*x==10^30-1,x,10]]")
        self.assertEqual(result.status, "unverified")
        self.assertTrue(result.warnings)

    def test_rounding_checks_preserve_boolean_branches(self):
        irrational = evaluate("Assuming[Not[Element[x,Integers]],NSolve[x^2==2,x]]")
        self.assertNotEqual(irrational.status, "unverified")
        rounded = evaluate("Assuming[Or[x==0,x>1],NSolve[10^30*x==10^30+1,x,10]]")
        self.assertEqual(rounded.status, "unverified")

    def test_unsupported_inputs_fail_without_changing_a_session(self):
        session = Session()
        session.evaluate("a=7")
        for source in (
            "NSolve[x^2-2,x]", "NSolve[{x==1,y==2},{x,x}]",
            "NSolve[Sin[x]==0,x]", "NSolve[x^2==a,x]",
            "NSolve[x^33==1,x]", "NSolve[x==1,x,9]", "NSolve[x==1,x,201]",
            "NSolve[x==1,x,30/2+1/2]", "NSolve[x==1,x,Reals,10,20]",
            "NSolve[x==1,x,False]",
        ):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, evaluate, source)
                self.assertEqual(session.evaluate("a").text, "7")


if __name__ == "__main__":
    unittest.main()
