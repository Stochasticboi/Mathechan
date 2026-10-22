"""Exact references and residual checks for the symbolic calculus backend."""

import unittest
from unittest.mock import patch

import sympy as sp

from mathechan.calculus import integrate_expression, solve_equations, solve_ode


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.x = sp.Symbol("x")

    def test_polynomial_antiderivative_and_constant_warning(self):
        result = integrate_expression(3 * self.x**2 + 2 * self.x, self.x)
        self.assertEqual(sp.expand(result.value - (self.x**3 + self.x**2)), 0)
        self.assertEqual(sp.diff(result.value, self.x), 3 * self.x**2 + 2 * self.x)
        self.assertEqual(result.status, "evaluated")
        self.assertEqual(result.details["verification"], "verified")
        self.assertTrue(any("constante" in message for message in result.warnings))

    def test_definite_polynomial_and_reversed_bounds(self):
        result = integrate_expression(self.x**2, self.x, (sp.S.Zero, sp.Integer(3)))
        self.assertEqual(result.value, 9)
        reverse = integrate_expression(self.x**2, self.x, (sp.Integer(3), sp.S.Zero))
        self.assertEqual(reverse.value, -9)
        self.assertEqual(result.details["verification"], "not_checked")

    def test_gaussian_integral_on_the_real_line(self):
        result = integrate_expression(sp.exp(-(self.x**2)), self.x, (-sp.oo, sp.oo))
        self.assertEqual(result.value, sp.sqrt(sp.pi))

    def test_conditional_integral_preserves_piecewise_and_pending_branch(self):
        a = sp.Symbol("a")
        result = integrate_expression(sp.exp(-a * self.x), self.x, (sp.S.Zero, sp.oo))
        self.assertTrue(result.value.has(sp.Piecewise))
        self.assertTrue(result.value.has(sp.Integral))
        self.assertEqual(result.value.subs(a, 2), sp.Rational(1, 2))
        self.assertEqual(result.status, "unresolved")
        self.assertTrue(result.conditions)
        self.assertTrue(any("alternativas" in message for message in result.warnings))

    def test_unevaluated_integral_is_explicit(self):
        f = sp.Function("f")
        result = integrate_expression(f(self.x), self.x)
        self.assertEqual(result.value, sp.Integral(f(self.x), self.x))
        self.assertEqual(result.status, "unresolved")

    def test_piecewise_antiderivative_is_conditional(self):
        a = sp.Symbol("a")
        result = integrate_expression(self.x**a, self.x)
        self.assertTrue(result.value.has(sp.Piecewise))
        self.assertFalse(result.value.has(sp.Integral))
        self.assertEqual(result.status, "conditional")
        self.assertEqual(sp.diff(result.value.subs(a, 2), self.x), self.x**2)

    def test_unconditional_divergence_and_conditional_branches_differ(self):
        a = sp.Symbol("a", real=True)
        branch_result = sp.Piecewise((sp.S.One, a > 0), (sp.oo, True))
        with patch("mathechan.calculus.sp.integrate", return_value=branch_result):
            result = integrate_expression(self.x, self.x, (sp.S.Zero, sp.S.One))
        self.assertEqual(result.status, "conditional")
        self.assertEqual(result.value.subs(a, 1), 1)
        self.assertTrue(any("divergentes" in message for message in result.warnings))

    def test_divergent_integrals_do_not_report_finite_results(self):
        for expression, bounds in (
            (1 / self.x, (-sp.S.One, sp.S.One)),
            (1 / self.x**2, (-sp.S.One, sp.S.One)),
            (sp.sin(self.x), (sp.S.Zero, sp.oo)),
        ):
            with (
                self.subTest(expression=expression),
                self.assertRaisesRegex(ValueError, "diverge|convergente"),
            ):
                integrate_expression(expression, self.x, bounds)

    def test_invalid_variables_and_complex_bounds_are_rejected(self):
        with self.assertRaises(ValueError):
            integrate_expression(self.x, self.x + 1)
        with self.assertRaises(ValueError):
            integrate_expression(self.x, self.x, (sp.I, sp.S.One))
        with self.assertRaises(ValueError):
            integrate_expression(self.x, self.x, (self.x, sp.S.One))


class AlgebraicSolveTests(unittest.TestCase):
    def setUp(self):
        self.x, self.y = sp.symbols("x y")

    def test_quadratic_finite_roots_have_exact_zero_residual(self):
        equation = sp.Eq(self.x**2, 4, evaluate=False)
        result = solve_equations(equation, self.x)
        self.assertEqual(result.value, sp.FiniteSet(-2, 2))
        self.assertEqual(result.details["verification"], "verified")
        for root in result.value:
            self.assertEqual(equation.lhs.subs(self.x, root) - equation.rhs, 0)

    def test_domains_distinguish_no_real_roots_from_complex_roots(self):
        equation = sp.Eq(self.x**2 + 1, 0, evaluate=False)
        self.assertEqual(
            solve_equations(equation, self.x).value, sp.FiniteSet(-sp.I, sp.I)
        )
        result = solve_equations(equation, self.x, "Reals")
        self.assertEqual(result.value, sp.S.EmptySet)
        self.assertEqual(result.status, "no_solution")

    def test_radical_candidates_are_checked_in_original_equation(self):
        equation = sp.Eq(sp.sqrt(self.x + 1), self.x - 1, evaluate=False)
        result = solve_equations(equation, self.x, "Reals")
        self.assertEqual(result.value, sp.FiniteSet(3))
        self.assertEqual(
            sp.simplify(equation.lhs.subs(self.x, 3) - equation.rhs.subs(self.x, 3)), 0
        )

    def test_linear_system_has_exact_residuals(self):
        equations = [sp.Eq(2 * self.x + self.y, 3), sp.Eq(self.x - self.y, 0)]
        result = solve_equations(equations, [self.x, self.y])
        self.assertEqual(result.value, sp.FiniteSet(sp.Tuple(1, 1)))
        self.assertEqual(result.details["verification"], "verified")
        for equation in equations:
            self.assertEqual(
                (equation.lhs - equation.rhs).subs({self.x: 1, self.y: 1}), 0
            )

    def test_parameterized_linear_family_is_not_a_single_point(self):
        result = solve_equations([sp.Eq(self.x + self.y, 1)], [self.x, self.y])
        self.assertEqual(result.value, sp.FiniteSet(sp.Tuple(1 - self.y, self.y)))
        self.assertTrue(result.warnings)
        self.assertEqual(result.details["verification"], "verified")

    def test_inconsistent_system_and_rational_equation(self):
        inconsistent = solve_equations(
            [sp.Eq(self.x + self.y, 1), sp.Eq(self.x + self.y, 2)], [self.x, self.y]
        )
        self.assertEqual(inconsistent.status, "no_solution")
        self.assertEqual(
            solve_equations(sp.Eq(1 / self.x, 0), self.x).status, "no_solution"
        )

    def test_infinite_set_and_identity_are_kept_as_sets(self):
        result = solve_equations(sp.Eq(sp.sin(self.x), 0), self.x, "Reals")
        self.assertTrue(result.value.contains(0))
        self.assertTrue(result.value.contains(sp.pi))
        self.assertFalse(result.value.is_FiniteSet)
        identity = solve_equations(sp.Eq(self.x, self.x, evaluate=False), self.x)
        self.assertEqual(identity.value, sp.S.Complexes)

    def test_parameter_degeneracy_is_not_silently_discarded(self):
        a = sp.Symbol("a")
        result = solve_equations(sp.Eq(a * self.x, 0, evaluate=False), self.x)
        self.assertEqual(result.status, "unresolved")
        self.assertTrue(result.value.has(sp.ConditionSet))
        self.assertIs(result.value.condition.subs(a, 0), sp.S.true)
        self.assertIs(result.value.condition.subs({a: 1, self.x: 7}), sp.S.false)

    def test_invalid_domain_and_nonlinear_family(self):
        with self.assertRaises(ValueError):
            solve_equations(sp.Eq(self.x, 1), self.x, "Integers")
        outcome = solve_equations([sp.Eq(self.x**2 + self.y, 1)], [self.x, self.y])
        self.assertIn(outcome.status, ("conditional", "unresolved"))
        self.assertTrue(outcome.conditions or outcome.warnings)


class OdeTests(unittest.TestCase):
    def setUp(self):
        self.x = sp.Symbol("x")
        self.y = sp.Function("y")
        self.dependent = self.y(self.x)

    def test_exponential_decay_with_initial_value(self):
        equation = sp.Eq(sp.diff(self.dependent, self.x), -self.dependent)
        result = solve_ode([equation, sp.Eq(self.y(0), 2)], self.dependent, self.x)
        self.assertEqual(result.value, sp.Eq(self.dependent, 2 * sp.exp(-self.x)))
        solution = result.value.rhs
        self.assertEqual(sp.diff(solution, self.x) + solution, 0)
        self.assertEqual(solution.subs(self.x, 0), 2)
        self.assertEqual(result.status, "verified")
        self.assertEqual(result.details["initial_residuals"], ["0"])

    def test_separable_first_order_family(self):
        equation = sp.Eq(sp.diff(self.dependent, self.x), self.x * self.dependent)
        result = solve_ode(equation, self.dependent, self.x)
        solution = result.value.rhs
        self.assertEqual(sp.simplify(sp.diff(solution, self.x) - self.x * solution), 0)
        self.assertEqual(result.status, "verified")
        self.assertTrue(result.warnings)

    def test_second_order_oscillator_and_derivative_initial_value(self):
        equation = sp.Eq(sp.diff(self.dependent, self.x, 2) + self.dependent, 0)
        velocity = sp.Subs(sp.diff(self.dependent, self.x), self.x, 0)
        result = solve_ode(
            [equation, sp.Eq(self.y(0), 1), sp.Eq(velocity, 0)], self.dependent, self.x
        )
        self.assertEqual(result.value.rhs, sp.cos(self.x))
        solution = result.value.rhs
        self.assertEqual(sp.diff(solution, self.x, 2) + solution, 0)
        self.assertEqual(solution.subs(self.x, 0), 1)
        self.assertEqual(sp.diff(solution, self.x).subs(self.x, 0), 0)
        self.assertEqual(result.status, "verified")

    def test_contradictory_initial_values_are_rejected(self):
        equation = sp.Eq(sp.diff(self.dependent, self.x), self.dependent)
        with self.assertRaisesRegex(ValueError, "incompatibles"):
            solve_ode(
                [equation, sp.Eq(self.y(0), 1), sp.Eq(self.y(0), 2)],
                self.dependent,
                self.x,
            )

    def test_incompatible_data_at_distinct_points_are_rejected(self):
        equation = sp.Eq(sp.diff(self.dependent, self.x), 0)
        with self.assertRaisesRegex(ValueError, "condiciones iniciales"):
            solve_ode(
                [equation, sp.Eq(self.y(0), 1), sp.Eq(self.y(1), 2)],
                self.dependent,
                self.x,
            )

    def test_singular_initial_point_cannot_be_verified_by_cancellation(self):
        equations = (
            sp.Eq(sp.diff(self.dependent, self.x), 1 / self.dependent),
            sp.Eq(
                sp.diff(self.dependent, self.x) / self.x,
                self.dependent / self.x,
                evaluate=False,
            ),
        )
        for equation, initial in zip(equations, (0, 1)):
            with self.subTest(equation=equation):
                result = solve_ode(
                    [equation, sp.Eq(self.y(0), initial)], self.dependent, self.x
                )
                self.assertEqual(result.status, "unverified")
                self.assertFalse(result.details["initial_defined"])
                self.assertTrue(
                    any("definida y finita" in message for message in result.warnings)
                )

    def test_pde_multiple_functions_and_third_order_are_rejected(self):
        t = sp.Symbol("t")
        g = sp.Function("g")
        examples = (
            (
                sp.Eq(sp.Derivative(self.y(self.x, t), self.x), self.y(self.x, t)),
                self.y(self.x, t),
            ),
            (sp.Eq(sp.diff(self.dependent, self.x), g(self.x)), self.dependent),
            (sp.Eq(sp.diff(self.dependent, self.x, 3), self.dependent), self.dependent),
        )
        for equation, dependent in examples:
            with self.subTest(equation=equation), self.assertRaises(ValueError):
                solve_ode(equation, dependent, self.x)

    def test_backend_not_implemented_is_unresolved(self):
        equation = sp.Eq(sp.diff(self.dependent, self.x), self.dependent)
        with patch("mathechan.calculus.sp.dsolve", side_effect=NotImplementedError):
            result = solve_ode(equation, self.dependent, self.x)
        self.assertEqual(result.status, "unresolved")
        self.assertEqual(result.value, equation)

    def test_truncated_series_is_not_an_exact_solution(self):
        equation = sp.Eq(sp.diff(self.dependent, self.x), self.dependent)
        series = sp.Eq(self.dependent, 1 + self.x + sp.Order(self.x**2))
        with patch("mathechan.calculus.sp.dsolve", return_value=series):
            result = solve_ode(equation, self.dependent, self.x)
        self.assertEqual(result.status, "unresolved")
        self.assertTrue(any("serie truncada" in message for message in result.warnings))

    def test_bad_backend_solution_cannot_receive_verified_status(self):
        equation = sp.Eq(sp.diff(self.dependent, self.x), self.dependent)
        with patch(
            "mathechan.calculus.sp.dsolve", return_value=sp.Eq(self.dependent, self.x)
        ):
            result = solve_ode([equation, sp.Eq(self.y(0), 1)], self.dependent, self.x)
        self.assertEqual(result.status, "unverified")
        self.assertNotEqual(result.details["initial_residuals"], ["0"])


if __name__ == "__main__":
    unittest.main()
