"""Acceptance cases for extended definitions, algebra, domains and precision."""

import json
import unittest

import sympy as sp

from mathechan import MathechanError, Session, evaluate
from mathechan.kernel import Parser, build


class ExtendedLanguageTests(unittest.TestCase):
    def value(self, source):
        return build(Parser(source).parse())

    def test_full_simplify_keeps_domains_and_complex_branches(self):
        self.assertEqual(evaluate("FullSimplify[Sin[x]^2+Cos[x]^2]").text, "1")
        self.assertEqual(evaluate("FullSimplify[Sqrt[x^2],x>0]").text, "x")
        self.assertIn("sqrt", evaluate("FullSimplify[Sqrt[x^2]]").text)
        self.assertTrue(evaluate("FullSimplify[(x^2-1)/(x-1)]").conditions)
        self.assertRaises(MathechanError, evaluate,
                          "Substitute[FullSimplify[(x^2-1)/(x-1)],x,1]")

    def test_nonlinear_symbolic_system_has_verified_points(self):
        points = self.value("Solve[{x^2+y^2==1,x-y==0},{x,y}]")
        self.assertEqual(len(points), 2)
        for x, y in points:
            self.assertEqual(sp.simplify(x*x+y*y-1), 0)
            self.assertEqual(sp.simplify(x-y), 0)

    def test_numeric_system_retains_all_enumerated_algebraic_points(self):
        points = self.value("NSolve[{x^2+y^2==1,x-y==0},{x,y},Reals,40]")
        self.assertEqual(len(points), 2)
        for x, y in points:
            self.assertLess(abs(x*x+y*y-1), sp.Rational(1,10)**35)

    def test_seeded_transcendental_solve_is_explicitly_local(self):
        result = evaluate("NSolve[Cos[x]==x,x,{1},40]")
        point = next(iter(self.value("NSolve[Cos[x]==x,x,{1},40]")))
        self.assertLess(abs(point-sp.Float("0.7390851332151606416553120876738734040134",40)),
                        sp.Rational(1,10)**38)
        self.assertFalse(result.details["completeness"])
        self.assertTrue(result.warnings)

    def test_algebraic_coefficients_and_approximate_inputs(self):
        points = self.value("NSolve[Sqrt[2]*x==1,x,40]")
        self.assertLess(abs(next(iter(points))-sp.sqrt(2).evalf(40)/2), sp.Rational(1,10)**38)
        result = evaluate("NSolve[N[1/10,15]*x==1,x,40]")
        self.assertFalse(result.exact)
        self.assertTrue(result.warnings)

    def test_reduce_and_original_domain(self):
        self.assertEqual(self.value("Reduce[And[x>0,x<2],x,Reals]"), sp.Interval.open(0,2))
        self.assertEqual(self.value("Reduce[x/x==1,x,Reals]"), sp.S.Reals-sp.FiniteSet(0))

    def test_domain_analysis_preserves_cancelled_exclusion(self):
        self.assertEqual(self.value("AnalyzeDomain[x/x,x,Reals]"), sp.S.Reals-sp.FiniteSet(0))
        domain = self.value("AnalyzeDomain[Log[x],x,Reals]")
        self.assertIs(domain.contains(-1), sp.false)
        self.assertIs(domain.contains(1), sp.true)

    def test_certified_numeric_result_has_a_rational_bound(self):
        result = evaluate("CertifiedN[Sqrt[2],40]")
        self.assertFalse(result.exact)
        self.assertTrue(result.details["certified"])
        json.dumps(result.to_dict(), allow_nan=False)
        self.assertRaises(MathechanError, evaluate, "CertifiedN[Pi,40]")

    def test_recursive_pattern_function_and_lazy_if(self):
        session = Session()
        session.evaluate("DefinePattern[fac,{IntegerPattern[n]},If[n<=1,1,n*fac[n-1]]]")
        self.assertEqual(session.evaluate("fac[6]").text, "720")
        self.assertRaises(MathechanError, session.evaluate, "fac[1/2]")
        self.assertEqual(evaluate("If[True,3,1/0]").text, "3")

    def test_stored_containers_and_symbolic_hold(self):
        session = Session()
        session.evaluate("m=Matrix[{{1,2},{3,4}}]")
        self.assertEqual(session.evaluate("m").kind, "matrix")
        session.evaluate("h=Hold[1/0]")
        self.assertIn("Hold", session.evaluate("h").text)
        self.assertRaises(MathechanError, session.evaluate, "ReleaseHold[h]")

    def test_materialized_deferred_value_respects_its_assumptions(self):
        session = Session()
        session.evaluate("Assume[x>0]")
        session.evaluate("SetDelayed[x,-1]")
        self.assertRaises(MathechanError, session.evaluate, "x")
        self.assertRaises(MathechanError, session.evaluate, "Sqrt[x^2]")
        session.evaluate("SetDelayed[x,2]")
        self.assertEqual(session.evaluate("x").text, "2")


if __name__ == "__main__":
    unittest.main()
