"""End-to-end syntax, scoped operations, domains and structured query results."""

import contextlib
import io
import json
import unittest

import sympy as sp

from mathechan import MathechanError, evaluate
from mathechan.__main__ import main
from mathechan.kernel import Parser, build


class ScientificLanguageTests(unittest.TestCase):
    def value(self, source):
        return build(Parser(source).parse())

    def test_numerical_evaluation_preserves_approximation(self):
        result = evaluate("N[Pi,50]")
        self.assertFalse(result.exact)
        self.assertEqual(result.status, "approximate")
        self.assertIsNone(result.input)
        self.assertTrue(
            result.text.startswith(
                "3.1415926535897932384626433832795028841971693993751"
            )
        )
        self.assertEqual(
            result.details["numeric_evaluations"][0]["requested_significant_digits"], 50
        )
        self.assertEqual(evaluate("0.1+0.2").text, "3/10")
        self.assertTrue(evaluate("0.1+0.2").exact)

    def test_numerical_precision_errors_are_controlled(self):
        for source in (
            "N[x]",
            "N[Pi,0]",
            "N[Pi,1001]",
            "N[Pi,3/2]",
            "N[]",
            "N[Pi,2,3]",
        ):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, evaluate, source)

    def test_polynomial_factorization_is_exact(self):
        self.assertEqual(
            self.value("Factor[x^2-1]"), (sp.Symbol("x") - 1) * (sp.Symbol("x") + 1)
        )
        self.assertEqual(self.value("Substitute[Factor[x^2-1],x,3]"), 8)

    def test_rational_operations_keep_original_domains(self):
        self.assertEqual(
            self.value("Together[1/x+1/y]"),
            (sp.Symbol("x") + sp.Symbol("y")) / (sp.Symbol("x") * sp.Symbol("y")),
        )
        result = evaluate("Cancel[(x^2-1)/(x-1)]")
        self.assertEqual(result.text, "x + 1")
        self.assertTrue(any("x" in item for item in result.conditions))
        self.assertRaises(
            MathechanError, evaluate, "Substitute[Cancel[(x^2-1)/(x-1)],x,1]"
        )
        for source in ("Factor[Sin[x]]", "Together[Sin[x]/x]", "Cancel[N[1/3]]"):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, evaluate, source)

    def test_substitution_transforms_constraints(self):
        result = evaluate("Substitute[x/x,x,y]")
        self.assertEqual(result.text, "1")
        self.assertEqual(result.conditions, ("(y) != 0",))
        self.assertEqual(evaluate("Substitute[x/x,x,2]").conditions, ())
        self.assertRaises(MathechanError, evaluate, "Substitute[x/x,x,0]")
        self.assertEqual(evaluate("Substitute[D[x^3,x],x,2]").text, "12")

    def test_finite_sums_are_inclusive_and_exact(self):
        for source, expected in (
            ("Sum[n,{n,1,10}]", "55"),
            ("Sum[n^2,{n,1,3}]", "14"),
            ("Sum[1/n,{n,1,3}]", "11/6"),
            ("Sum[n,{n,-2,2}]", "0"),
            ("Sum[1/0,{n,2,1}]", "0"),
        ):
            with self.subTest(source=source):
                self.assertEqual(evaluate(source).text, expected)

    def test_substitution_resolves_integral_branches_without_stale_conditions(self):
        result = evaluate("Substitute[Integrate[Exp[-a*x],{x,0,Infinity}],a,1]")
        self.assertEqual(result.text, "1")
        self.assertEqual(result.conditions, ())
        self.assertEqual(result.status, "evaluated")
        indefinite = evaluate("Substitute[Integrate[Exp[-a*x],x],a,1]")
        self.assertEqual(
            self.value("Substitute[Integrate[Exp[-a*x],x],a,1]"),
            -sp.exp(-sp.Symbol("x")),
        )
        self.assertEqual(indefinite.conditions, ())
        self.assertTrue(
            any("constante aditiva" in item for item in indefinite.warnings)
        )
        self.assertRaises(
            MathechanError,
            evaluate,
            "Substitute[Integrate[Exp[-a*x],{x,0,Infinity}],a,-1]",
        )

    def test_substitution_preserves_real_bound_requirements(self):
        integral = "Integrate[x,{x,0,a}]"
        self.assertEqual(evaluate(integral).status, "conditional")
        self.assertRaises(
            MathechanError, evaluate, f"Substitute[{integral},a,Sqrt[-1]]"
        )
        self.assertEqual(evaluate(f"Substitute[{integral},a,2]").text, "2")
        renamed = evaluate(f"Substitute[{integral},a,b]")
        self.assertEqual(renamed.status, "conditional")
        self.assertTrue(
            any(
                "Contains(b," in item and "Reals" in item for item in renamed.conditions
            )
        )
        self.assertRaises(
            MathechanError,
            evaluate,
            f"Substitute[Substitute[{integral},a,b],b,Sqrt[-1]]",
        )
        # Infinite integration endpoints are accepted directly; substitution
        # itself accepts finite scalars and does not stand for taking a limit.
        self.assertRaises(
            MathechanError,
            evaluate,
            "Substitute[Integrate[Exp[-x],{x,0,a}],a,Infinity]",
        )
        other_bound = evaluate("Substitute[Integrate[x,{x,a,b}],a,1]")
        self.assertTrue(any("Contains(b," in item for item in other_bound.conditions))

    def test_sum_scopes_nested_indices_and_held_variables(self):
        cases = (
            ("Sum[Sum[n,{n,1,2}],{n,1,3}]", "9"),
            ("Sum[Sum[k,{k,1,n}],{n,1,3}]", "10"),
            ("Sum[D[n^2,n],{n,1,3}]", "12"),
            ("Sum[Substitute[n,n,7],{n,1,3}]", "21"),
            ("Sum[n/n,{n,1,3}]", "3"),
        )
        for source, expected in cases:
            with self.subTest(source=source):
                result = evaluate(source)
                self.assertEqual(result.text, expected)
                self.assertEqual(result.conditions, ())

    def test_sum_rejects_holes_and_enforces_nested_budget(self):
        for source in (
            "Sum[0/n,{n,0,1}]",
            "Sum[n/n,{n,0,1}]",
            "Sum[n,{n,1,1001}]",
            "Sum[n,{n,0,1/2}]",
            "Sum[Sum[k,{k,1,1000}],{n,1,3}]",
        ):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, evaluate, source)
        divergent = evaluate("Sum[n,{n,0,Infinity}]")
        self.assertEqual(divergent.status, "divergent")
        self.assertIn("Sum", divergent.text)

    def test_equalities_are_inert_and_lists_roundtrip(self):
        equation = self.value("x/x==1")
        self.assertIsInstance(equation, sp.Equality)
        self.assertIsNot(equation, sp.S.true)
        result = evaluate("{x==1,y==2}")
        self.assertEqual(result.kind, "list")
        self.assertIsNotNone(result.input)
        self.assertEqual(self.value(result.input), self.value("{x==1,y==2}"))
        self.assertRaises(MathechanError, evaluate, "x==y==z")
        self.assertRaises(MathechanError, evaluate, "x=2")

    def test_integrals_match_exact_reference_values(self):
        self.assertEqual(evaluate("Integrate[x^2,{x,0,1}]").text, "1/3")
        self.assertEqual(evaluate("Integrate[Exp[-x],{x,0,Infinity}]").text, "1")
        antiderivative = self.value("Integrate[Sin[x],x]")
        self.assertEqual(
            sp.diff(antiderivative, sp.Symbol("x")), sp.sin(sp.Symbol("x"))
        )
        self.assertTrue(evaluate("Integrate[Sin[x],x]").warnings)

    def test_integral_bound_conditions_do_not_leak_as_free_constraints(self):
        result = evaluate("Integrate[x/x,{x,-1,1}]")
        self.assertEqual(result.text, "2")
        self.assertEqual(result.conditions, ())
        self.assertTrue(result.details.get("integrand_conditions"))
        self.assertRaises(MathechanError, evaluate, "Integrate[1/x,{x,-1,1}]")

    def test_scalar_equations_and_original_denominator_exclusions(self):
        self.assertEqual(self.value("Solve[x^2==4,x]"), sp.FiniteSet(-2, 2))
        result = evaluate("Solve[(1/x)^(-1)==0,x]")
        self.assertEqual(result.status, "no_solution")
        self.assertEqual(self.value("Solve[x^2+1==0,x,Reals]"), sp.S.EmptySet)
        identity = self.value("Solve[x/x==1,x,Reals]")
        self.assertFalse(identity.contains(0))
        self.assertTrue(identity.contains(2))

    def test_linear_system_has_independently_checked_solution(self):
        value = self.value("Solve[{x+y==3,x-y==1},{x,y}]")
        self.assertEqual(value, sp.FiniteSet(sp.Tuple(2, 1)))
        x, y = next(iter(value))
        self.assertEqual(x + y, 3)
        self.assertEqual(x - y, 1)

    def test_equation_system_exclusions_filter_single_variable_tuples(self):
        result = evaluate("Solve[{x/x==1,x==0},x]")
        self.assertEqual(result.status, "no_solution")
        self.assertEqual(self.value("Solve[{x/x==1,x==0},x]"), sp.S.EmptySet)
        family = evaluate("Solve[{x/x==1,y==0},{x,y}]")
        self.assertEqual(family.status, "conditional")
        self.assertTrue(any("x" in condition for condition in family.conditions))
        self.assertTrue(evaluate("Solve[x/(a*x)==1/a,x]").conditions)
        real_family = evaluate("Solve[{x/x==1,y==0},{x,y},Reals]")
        self.assertEqual(real_family.status, "conditional")
        self.assertTrue(real_family.conditions)

    def test_ode_general_and_initial_value_solutions(self):
        result = evaluate("DSolve[D[y[x],x]==y[x],y[x],x]")
        self.assertEqual(result.kind, "solutions")
        self.assertIn(result.status, ("verified", "solved"))
        solution = self.value("DSolve[{D[y[x],x]==-2*y[x],y[0]==3},y[x],x]")
        self.assertIsInstance(solution, sp.Equality)
        x = sp.Symbol("x")
        self.assertEqual(solution.rhs.subs(x, 0), 3)
        self.assertEqual(sp.simplify(sp.diff(solution.rhs, x) + 2 * solution.rhs), 0)

    def test_second_order_ode_residual(self):
        solution = self.value("DSolve[D[D[y[x],x],x]+y[x]==0,y[x],x]")
        x = sp.Symbol("x")
        self.assertEqual(sp.simplify(sp.diff(solution.rhs, x, 2) + solution.rhs), 0)

    def test_ode_initial_values_cannot_bypass_original_domain(self):
        for source in (
            "DSolve[{D[y[x],x]/x==y[x]/x,y[0]==1},y[x],x]",
            "DSolve[{D[y[x],x]==1/y[x],y[0]==0},y[x],x]",
        ):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, evaluate, source)
        regular = evaluate("DSolve[{D[y[x],x]/x==y[x]/x,y[1]==1},y[x],x]")
        self.assertEqual(regular.status, "conditional")
        self.assertTrue(regular.conditions)
        self.assertEqual(regular.details["initial_residuals"], ["0"])

    def test_unknown_functions_do_not_escape_ode_scope(self):
        for source in (
            "y[x]",
            "open[x]",
            "DSolve[D[y[x],x]==z[x],y[x],x]",
            "DSolve[D[y[x],x]==y[x],y[x],Pi]",
        ):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, evaluate, source)

    def test_cli_prints_solutions_and_serializes_new_results(self):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(main(["Solve[x^2==4,x]", "--json"]), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["kind"], "solutions")
        self.assertEqual(errors.getvalue(), "")
        for source in (
            "N[Pi,30]",
            "Factor[x^2-1]",
            "Sum[n,{n,1,4}]",
            "Integrate[x,{x,0,1}]",
            "DSolve[D[y[x],x]==y[x],y[x],x]",
        ):
            with self.subTest(source=source):
                json.dumps(evaluate(source).to_dict(), allow_nan=False)


if __name__ == "__main__":
    unittest.main()
