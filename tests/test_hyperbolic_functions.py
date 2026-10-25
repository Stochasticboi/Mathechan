"""Hyperbolic calculus, principal branches and persistent pole exclusions."""

import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sympy as sp

from mathechan import MathechanError, Session, evaluate
from mathechan.kernel import Parser, build


FUNCTIONS = {
    "Sinh": sp.sinh, "Cosh": sp.cosh, "Tanh": sp.tanh,
    "Coth": sp.coth, "Sech": sp.sech, "Csch": sp.csch,
    "ArcSinh": sp.asinh, "ArcCosh": sp.acosh, "ArcTanh": sp.atanh,
    "ArcCoth": sp.acoth, "ArcSech": sp.asech, "ArcCsch": sp.acsch,
}


def value(source):
    return build(Parser(source).parse())


class HyperbolicFunctionsTests(unittest.TestCase):
    def assert_zero(self, expression):
        self.assertEqual(sp.simplify(sp.trigsimp(expression).rewrite(sp.exp)), 0)

    def test_direct_functions_and_exact_values(self):
        for source, expected in (("Sinh[0]",0),("Cosh[0]",1),("Tanh[0]",0),
                                 ("Sech[0]",1),("Coth[Log[2]]",sp.Rational(5,3)),
                                 ("Csch[Log[2]]",sp.Rational(4,3))):
            with self.subTest(source=source):
                self.assert_zero(value(source)-expected)

    def test_six_direct_derivative_identities(self):
        x = sp.Symbol("x")
        derivatives = {
            "Sinh": sp.cosh(x), "Cosh": sp.sinh(x), "Tanh": sp.sech(x)**2,
            "Coth": -sp.csch(x)**2, "Sech": -sp.sech(x)*sp.tanh(x),
            "Csch": -sp.csch(x)*sp.coth(x),
        }
        for name, expected in derivatives.items():
            with self.subTest(name=name):
                self.assert_zero(value(f"D[{name}[x],x]")-expected)

    def test_inverse_derivatives_at_branch_interior_points(self):
        x = sp.Symbol("x")
        # Positive interior points avoid confusing local real identities with
        # identities valid on every complex principal branch.
        references = {
            "ArcSinh": (sp.Integer(2),1/sp.sqrt(1+x*x)),
            "ArcCosh": (sp.Integer(2),1/(sp.sqrt(x-1)*sp.sqrt(x+1))),
            "ArcTanh": (sp.Rational(1,2),1/(1-x*x)),
            "ArcCoth": (sp.Integer(2),1/(1-x*x)),
            "ArcSech": (sp.Rational(1,2),-1/(x*sp.sqrt(1-x*x))),
            "ArcCsch": (sp.Integer(2),-1/(x*sp.sqrt(1+x*x))),
        }
        for name, (point, expected) in references.items():
            with self.subTest(name=name):
                observed = value(f"D[{name}[x],x]")
                difference = (observed-expected).subs(x,point).evalf(60)
                self.assertLess(abs(difference),sp.Rational(1,10**50))

    def test_chain_higher_and_mixed_derivatives(self):
        x, y = sp.symbols("x y")
        self.assert_zero(value("D[Sinh[3*x^2],x]")-6*x*sp.cosh(3*x*x))
        self.assert_zero(value("D[Cosh[x],{x,4}]")-sp.cosh(x))
        expected = sp.cosh(x*y)+x*y*sp.sinh(x*y)
        self.assert_zero(value("D[Sinh[x*y],x,y]")-expected)

    def test_direct_antiderivatives_have_zero_derivative_residual(self):
        x = sp.Symbol("x")
        for name in ("Sinh","Cosh","Tanh","Coth","Sech","Csch"):
            with self.subTest(name=name):
                primitive = value(f"Integrate[{name}[x],x]")
                self.assertFalse(primitive.has(sp.Integral))
                self.assert_zero(sp.diff(primitive,x)-FUNCTIONS[name](x))

    def test_inverse_asinh_antiderivative_residual(self):
        x = sp.Symbol("x")
        primitive = value("Integrate[ArcSinh[x],x]")
        self.assertFalse(primitive.has(sp.Integral))
        self.assert_zero(sp.diff(primitive,x)-sp.asinh(x))

    def test_definite_integrals_against_exact_closed_forms(self):
        for source, expected in (
            ("Integrate[Sinh[x],{x,0,Log[2]}]",sp.Rational(1,4)),
            ("Integrate[Cosh[x],{x,0,Log[2]}]",sp.Rational(3,4)),
            ("Integrate[Tanh[x],{x,0,Log[2]}]",sp.log(sp.Rational(5,4))),
        ):
            with self.subTest(source=source):
                self.assert_zero(value(source)-expected)

    def test_real_and_complex_principal_values(self):
        self.assert_zero(value("ArcSinh[1]")-sp.log(1+sp.sqrt(2)))
        self.assert_zero(value("ArcCosh[1/2]")-sp.I*sp.pi/3)
        self.assert_zero(value("ArcSech[2]")-sp.I*sp.pi/3)
        branch_difference = (value("ArcTanh[2]")-(sp.log(3)/2-sp.I*sp.pi/2)).evalf(60)
        self.assertLess(abs(branch_difference),sp.Rational(1,10**50))
        self.assert_zero(value("Cosh[Sqrt[-1]*Pi]")+1)

    def test_numeric_precision_against_independent_exponential_identity(self):
        observed = value("N[Tanh[1],50]")
        expected = ((sp.E**2-1)/(sp.E**2+1)).evalf(70)
        self.assertLess(abs(observed-expected),sp.Rational(1,10**48))
        self.assertFalse(evaluate("N[ArcSinh[1],50]").exact)

    def test_poles_are_controlled_errors(self):
        for source in ("Coth[0]","Csch[0]","Tanh[Sqrt[-1]*Pi/2]",
                       "Sech[Sqrt[-1]*Pi/2]","ArcTanh[1]","ArcTanh[-1]",
                       "ArcCoth[1]","ArcCoth[-1]","ArcSech[0]","ArcCsch[0]"):
            with self.subTest(source=source), self.assertRaises(MathechanError):
                evaluate(source)

    def test_pole_exclusions_survive_cancellation_and_replacement(self):
        cases = (
            ("Simplify[Coth[x]*Sinh[x]]","x->0"),
            ("Simplify[Csch[x]*Sinh[x]]","x->0"),
            ("Simplify[Sech[x]*Cosh[x]]","x->Sqrt[-1]*Pi/2"),
            ("Simplify[Tanh[x]*Cosh[x]]","x->Sqrt[-1]*Pi/2"),
            ("ArcTanh[x]-ArcTanh[x]","x->1"),
            ("ArcCoth[x]-ArcCoth[x]","x->-1"),
            ("ArcSech[x]-ArcSech[x]","x->0"),
            ("ArcCsch[x]-ArcCsch[x]","x->0"),
        )
        for expression, rule in cases:
            with self.subTest(expression=expression):
                self.assertTrue(evaluate(expression).conditions)
                with self.assertRaises(MathechanError):
                    evaluate(f"({expression})/.{rule}")

    def test_derivative_branch_point_exclusions_survive_cancellation(self):
        for name, point in (("ArcSinh","Sqrt[-1]"),("ArcCosh","1"),
                            ("ArcSech","1"),("ArcCsch","Sqrt[-1]")):
            source = f"D[{name}[x],x]-D[{name}[x],x]"
            with self.subTest(name=name):
                self.assertTrue(evaluate(source).conditions)
                self.assertRaises(MathechanError,evaluate,f"({source})/.x->{point}")

    def test_vector_derivative_exclusions_survive_zero_scaling(self):
        for source in ("Grad[ArcSinh[x],{x}]", "Hessian[ArcSinh[x],{x}]",
                       "Jacobian[{ArcSinh[x]},{x}]", "Div[{ArcSinh[x]},{x}]"):
            with self.subTest(source=source):
                self.assertTrue(evaluate(source).conditions)
                self.assertRaises(MathechanError,evaluate,f"(0*{source})/.x->Sqrt[-1]")

    def test_all_function_names_have_reusable_scalar_input(self):
        for name, constructor in FUNCTIONS.items():
            with self.subTest(name=name):
                result = evaluate(f"{name}[x]")
                self.assertIsNotNone(result.input)
                self.assertEqual(value(result.input),constructor(sp.Symbol("x")))

    def test_save_load_preserves_functions_and_poles_without_source_execution(self):
        session = Session()
        session.evaluate("v={"+",".join(f"{name}[x]" for name in FUNCTIONS)+"}")
        session.evaluate("c=Simplify[Sech[x]*Cosh[x]]")
        session.evaluate("DefineDelayed[f,{x},Sinh[x]+Tanh[x]]")
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory)/"hyperbolic.json"
            session.save(path)
            with patch("mathechan.kernel.build",side_effect=AssertionError("source executed on load")):
                loaded = Session.load(path)
            self.assertEqual(loaded.evaluate("v").text,session.evaluate("v").text)
            self.assertEqual(loaded.evaluate("f[0]").text,"0")
            self.assertRaises(MathechanError,loaded.evaluate,"c/.x->Sqrt[-1]*Pi/2")
            self.assertEqual(loaded.evaluate("c/.x->0").text,"1")

    def test_plot_hyperbolic_curve_and_reject_sampled_pole(self):
        plot = evaluate("Plot[Sech[x],{x,-1,1}]")
        self.assertEqual(len(plot.points),201)
        for x, y in plot.points:
            self.assertAlmostEqual(y,1/math.cosh(x),places=12)
        self.assertRaises(MathechanError,evaluate,"Plot[Coth[x],{x,-1,1}]")

    def test_wrong_arity_shapes_and_protected_names(self):
        for name in FUNCTIONS:
            for source in (f"{name}[]",f"{name}[x,y]",f"{name}[{{x}}]"):
                with self.subTest(source=source),self.assertRaises(MathechanError):
                    evaluate(source)
            with self.subTest(name=name),self.assertRaises(MathechanError):
                Session().evaluate(name+"=1")


if __name__ == "__main__":
    unittest.main()
