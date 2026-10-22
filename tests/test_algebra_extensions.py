"""Reference identities, exclusions and variable scope for Collect and Apart."""

import unittest

import sympy as sp

from mathechan import MathechanError, Session, evaluate
from mathechan.kernel import Parser, build


class AlgebraExtensionTests(unittest.TestCase):
    def value(self, source):
        return build(Parser(source).parse())

    def test_collect_groups_coefficients_by_explicit_variable(self):
        x, a, b = sp.symbols("x a b")
        result = self.value("Collect[a*x+b*x+x^2,x]")
        self.assertEqual(result, x**2 + (a+b)*x)
        expanded = self.value("Collect[(x+1)^3,x]")
        self.assertEqual(expanded, x**3+3*x**2+3*x+1)

    def test_apart_has_independent_reference_and_exact_identity(self):
        x = sp.Symbol("x")
        result = self.value("Apart[1/(x*(x+1)),x]")
        self.assertEqual(result, 1/x - 1/(x+1))
        self.assertEqual(sp.cancel(result - 1/(x*(x+1))), 0)
        self.assertEqual(self.value("Substitute[Apart[1/(x*(x+1)),x],x,2]"), sp.Rational(1,6))

    def test_apart_handles_repeated_poles_and_rational_parameters(self):
        x, a = sp.symbols("x a")
        result = self.value("Apart[(2*x+1)/(x^2*(x+1)),x]")
        self.assertEqual(sp.cancel(result - (2*x+1)/(x**2*(x+1))), 0)
        result = self.value("Apart[1/(x*(x+a)),x]")
        self.assertIsInstance(result, sp.Piecewise)
        for parameter in (0, 2, -1):
            self.assertEqual(sp.cancel(result.subs(a, parameter) - 1/(x*(x+parameter))), 0)

    def test_original_exclusions_survive_transformation_and_storage(self):
        for source in ("Apart[(x^2-1)/(x-1),x]", "Collect[x/x+x,x]"):
            with self.subTest(source=source):
                result = evaluate(source)
                self.assertTrue(result.conditions)
        for source, point in (("Apart[(x^2-1)/(x-1),x]", 1),
                              ("Collect[x/x+x,x]", 0)):
            self.assertRaises(MathechanError, evaluate, f"Substitute[{source},x,{point}]")
        session = Session()
        session.evaluate("f=Apart[(x^2-1)/(x-1),x]")
        self.assertRaises(MathechanError, session.evaluate, "Substitute[f,x,1]")

    def test_apart_exposes_parameter_degeneracy_instead_of_dropping_it(self):
        source = "Apart[1/(x*(x+a)),x]"
        result = evaluate(source)
        self.assertEqual(result.status, "conditional")
        self.assertEqual(len(result.details["apart_branches"]), 2)
        self.assertEqual(self.value(f"Substitute[{source},a,0]"), sp.Symbol("x")**-2)
        self.assertEqual(self.value("Apart[Substitute[1/(x*(x+a)),a,0],x]"), sp.Symbol("x")**-2)

    def test_explicit_variable_shadows_session_value(self):
        session = Session()
        session.evaluate("x=7")
        session.evaluate("a=2")
        self.assertEqual(session.evaluate("Collect[a*x+x,x]").text, "3*x")
        result = session.evaluate("Apart[1/(x*(x+1)),x]")
        self.assertIn("x", result.text)
        self.assertEqual(session.evaluate("x").text, "7")

    def test_nested_iterators_bind_results_and_exclusions(self):
        result = evaluate("Sum[Apart[1/(x*(x+1)),x],{x,1,3}]")
        self.assertEqual(result.text, "3/4")
        self.assertFalse(result.conditions)
        self.assertRaises(MathechanError, evaluate,
                          "Sum[Apart[1/(x*(x+1)),x],{x,0,1}]")
        self.assertEqual(evaluate("Sum[Collect[x^2+2*x,x],{x,1,3}]").text, "26")

    def test_unsupported_inputs_and_growth_have_controlled_errors(self):
        for source in ("Collect[x]", "Apart[x]", "Collect[x,x+1]", "Apart[x,Pi]",
                       "Collect[1/x,x]", "Collect[Sin[x],x]", "Apart[Sin[x]/x,x]",
                       "Collect[(x+y+z)^100,x]", "Apart[N[1/3]/x,x]"):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, evaluate, source)


if __name__ == "__main__":
    unittest.main()
