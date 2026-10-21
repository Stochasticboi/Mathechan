"""Immediate numeric snapshots stay isolated, atomic, and outside bound scopes."""

import json
import unittest
from decimal import Decimal
from unittest.mock import patch

import sympy as sp

from mathechan import EvaluationResult, MathechanError, Session, evaluate
from mathechan.session import PROTECTED_NAMES


class SessionAssignmentTests(unittest.TestCase):
    def test_immediate_assignments_keep_snapshots(self):
        session = Session()
        result = session.evaluate("x = 2")
        self.assertEqual(result.text, "2")
        self.assertEqual(result.details["assignment"], {"name": "x"})
        session.evaluate("a=x+1")
        session.evaluate("x=4")
        self.assertEqual(session.evaluate("a").text, "3")
        self.assertEqual(session.evaluate("x").text, "4")
        session.evaluate("a=a+1")
        self.assertEqual(session.evaluate("a").text, "4")

    def test_sessions_and_stateless_evaluation_are_independent(self):
        first, second = Session(), Session()
        first.evaluate("x=2")
        self.assertEqual(second.evaluate("x").text, "x")
        second.evaluate("x=7")
        self.assertEqual(first.evaluate("x").text, "2")
        self.assertEqual(evaluate("x").text, "x")
        self.assertRaises(MathechanError, evaluate, "x=2")

    def test_exact_decimals_rationals_and_complex_scalars(self):
        session = Session()
        session.evaluate("a=0.1+0.2")
        session.evaluate("b=1/3")
        session.evaluate("z=Sqrt[-1]")
        session.evaluate("I=5")
        self.assertEqual(session.evaluate("a").text, "3/10")
        self.assertEqual(session.evaluate("3*b").text, "1")
        self.assertEqual(session.evaluate("z^2").text, "-1")
        self.assertEqual(session.evaluate("I").text, "5")
        self.assertTrue(session.evaluate("a").exact)

    def test_float_precision_is_not_rationalized_or_truncated_by_storage(self):
        session = Session()
        approximate = session.evaluate("p=N[Pi,50]")
        self.assertFalse(approximate.exact)
        self.assertEqual(approximate.status, "approximate")
        self.assertEqual(session.evaluate("p").text, approximate.text)
        session.evaluate("q=p")
        session.evaluate("p=N[Pi,15]")
        self.assertEqual(session.evaluate("q").text, approximate.text)
        self.assertFalse(session.evaluate("q").exact)
        self.assertLess(
            abs(Decimal(session.evaluate("N[q-Pi,15]").text)), Decimal("1e-49")
        )
        self.assertIsNone(session.evaluate("q").input)

    def test_equalities_do_not_assign(self):
        session = Session()
        session.evaluate("x=2")
        result = session.evaluate("x==3")
        self.assertEqual(result.kind, "equation")
        self.assertEqual(session.evaluate("x").text, "2")

    def test_invalid_assignments_leave_existing_definition_unchanged(self):
        session = Session()
        session.evaluate("x=5")
        for source in (
            "x=1/0",
            "x=y+1",
            "x={1,2}",
            "x=(1==1)",
            "x=Infinity",
            "x=Solve[t==1,t]",
            "x=Plot[t,{t,0,1}]",
            "x=Integrate[0,{t,0,a}]",
            "x=x/x+(z/z)",
            "x=y=1",
            "x=(y=1)",
            "x=2; y=3",
            "x=2\ny=3",
            "x[1]=2",
            "x:=2",
            "x=__import__('os')",
            "x=Clear[x]",
        ):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, session.evaluate, source)
                self.assertEqual(session.evaluate("x").text, "5")
                self.assertEqual(session.evaluate("y").text, "y")

    def test_unknown_self_reference_is_not_a_delayed_definition(self):
        session = Session()
        self.assertRaises(MathechanError, session.evaluate, "a=a+1")
        self.assertEqual(session.evaluate("a").text, "a")

    def test_unverified_numeric_outcome_cannot_be_committed(self):
        session = Session()
        session.evaluate("x=5")
        for status in ("conditional", "unverified", "unresolved"):
            result = EvaluationResult("expression", "2", status=status)
            with (
                self.subTest(status=status),
                patch(
                    "mathechan.session._evaluate_node",
                    return_value=(result, sp.Integer(2)),
                ),
            ):
                self.assertRaises(MathechanError, session.evaluate, "x=2")
        self.assertEqual(session.evaluate("x").text, "5")

    def test_protected_constants_and_heads_cannot_be_redefined(self):
        session = Session()
        for name in PROTECTED_NAMES:
            with self.subTest(name=name):
                self.assertRaisesRegex(
                    MathechanError, "protegido", session.evaluate, name + "=2"
                )
        self.assertEqual(session.evaluate("Sin[Pi/2]").text, "1")

    def test_capacity_is_64_and_reassignment_at_capacity_is_atomic(self):
        session = Session()
        for index in range(64):
            session.evaluate(f"v{index}={index}")
        self.assertRaisesRegex(MathechanError, "64", session.evaluate, "overflow=1")
        session.evaluate("v0=99")
        self.assertEqual(session.evaluate("v0").text, "99")
        self.assertEqual(session.evaluate("v63").text, "63")
        self.assertEqual(session.evaluate("overflow").text, "overflow")

    def test_returned_metadata_cannot_mutate_a_stored_value(self):
        session = Session()
        assigned = session.evaluate("a=1/3")
        assigned.details.clear()
        self.assertEqual(session.evaluate("a").text, "1/3")
        json.dumps(session.evaluate("a").to_dict(), allow_nan=False)


class SessionScopeTests(unittest.TestCase):
    def setUp(self):
        self.session = Session()
        self.session.evaluate("x=3")
        self.session.evaluate("k=2")

    def test_derivative_shadows_global_and_uses_numeric_parameters(self):
        result = self.session.evaluate("D[k*x^2,x]")
        self.assertEqual(result.text, "4*x")
        self.assertEqual(evaluate(result.input).text, "4*x")
        self.assertEqual(self.session.evaluate(result.input).text, "12")
        self.assertTrue(any("sesión" in warning for warning in result.warnings))
        self.assertEqual(self.session.evaluate("x").text, "3")

    def test_sums_keep_lexical_binding_and_shadow_global_definitions(self):
        for source, expected in (
            ("Sum[x,{x,1,3}]", "6"),
            ("Sum[k*x,{x,1,3}]", "12"),
            ("Sum[D[x^2,x],{x,1,3}]", "12"),
            ("Sum[Integrate[x,x],{x,1,3}]", "7"),
            ("Sum[Substitute[x^2,x,2],{x,1,3}]", "12"),
            ("Sum[Sum[x/x,{x,1,2}],{x,0,1}]", "4"),
            ("D[Sum[x/n,{n,1,2}],x]", "3/2"),
        ):
            with self.subTest(source=source):
                self.assertEqual(self.session.evaluate(source).text, expected)

    def test_integrals_shadow_global_and_resolve_parameters_and_bounds(self):
        self.assertEqual(self.session.evaluate("Integrate[k*x,x]").text, "x**2")
        self.assertEqual(self.session.evaluate("Integrate[k*x,{x,0,1}]").text, "1")
        self.session.evaluate("b=2")
        self.assertEqual(self.session.evaluate("Integrate[x,{x,0,b}]").text, "2")

    def test_substitution_holds_target_but_resolves_replacement_parameters(self):
        self.assertEqual(self.session.evaluate("Substitute[x^2,x,2]").text, "4")
        self.assertEqual(self.session.evaluate("Substitute[x^2,x,x+1]").text, "16")

    def test_solve_shadows_every_requested_variable(self):
        result = self.session.evaluate("Solve[x^2==k,x]")
        self.assertEqual(result.text, "{-sqrt(2), sqrt(2)}")
        self.session.evaluate("y=7")
        self.assertEqual(
            self.session.evaluate("Solve[{x+y==k,x-y==0},{x,y}]").text, "{(1, 1)}"
        )

    def test_ode_variable_and_initial_data_ignore_external_x_and_y(self):
        self.session.evaluate("y=7")
        source = "DSolve[{D[y[x],x]==-k*y[x],y[0]==1},y[x],x]"
        result = self.session.evaluate(source)
        self.assertEqual(result.text, "Eq(y(x), exp(-2*x))")
        self.assertEqual(result.status, "verified")
        source = (
            "DSolve[{D[D[y[x],x],x]+k^2*y[x]==0,y[0]==0,"
            "Substitute[D[y[x],x],x,0]==k},y[x],x]"
        )
        result = self.session.evaluate(source)
        self.assertEqual(result.text, "Eq(y(x), sin(2*x))")
        self.assertEqual(result.details["initial_residuals"], ["0", "0"])

    def test_plot_shadows_variable_and_does_not_offer_context_dependent_input(self):
        result = self.session.evaluate("Plot[k*x,{x,0,1}]")
        self.assertEqual(result.points[100], (0.5, 1.0))
        self.assertEqual(result.points[-1], (1.0, 2.0))
        self.assertIsNone(result.input)
        self.assertTrue(any("sesión" in warning for warning in result.warnings))
        nested = self.session.evaluate("Plot[Sum[n*x,{n,1,2}],{x,0,1}]")
        self.assertEqual(nested.points[100], (0.5, 1.5))
        self.assertIsNotNone(evaluate("Plot[x,{x,0,1}]").input)
        self.assertIsNotNone(Session().evaluate("Plot[x,{x,0,1}]").input)
        json.dumps(result.to_dict(), allow_nan=False)


if __name__ == "__main__":
    unittest.main()
