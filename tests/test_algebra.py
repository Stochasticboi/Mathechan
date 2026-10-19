"""Reference identities, exact substitution and strict numerical evaluation."""

import unittest

import sympy as sp

from mathechan.algebra import (
    cancel_expression,
    factor_expression,
    numerical,
    substitute_expression,
    together_expression,
)


class AlgebraTests(unittest.TestCase):
    def setUp(self):
        self.x, self.y = sp.symbols("x y")

    def test_factor_exact_univariate_and_rational_content(self):
        x = self.x
        self.assertEqual(factor_expression(x**2 - 1), (x - 1) * (x + 1))
        self.assertEqual(
            factor_expression(x**2 / 3 - sp.Rational(1, 3)), (x - 1) * (x + 1) / 3
        )
        self.assertEqual(factor_expression(sp.Rational(-2, 3)), sp.Rational(-2, 3))

    def test_factor_exact_multivariate_identity(self):
        x, y = self.x, self.y
        result = factor_expression(x**2 - 2 * x * y + y**2)
        self.assertEqual(result, (x - y) ** 2)
        self.assertEqual(result.subs({x: 3, y: -2}), 25)
        self.assertEqual(factor_expression(x**2 + 1), x**2 + 1)

    def test_together_common_denominator_reference(self):
        x = self.x
        result = together_expression(1 / x + 1 / (x + 1))
        self.assertEqual(result, (2 * x + 1) / (x * (x + 1)))
        self.assertEqual(result.subs(x, 2), sp.Rational(5, 6))
        self.assertFalse(result.has(sp.Float))

    def test_cancel_rational_reference_and_sign(self):
        x, y = self.x, self.y
        self.assertEqual(cancel_expression((x**2 - 1) / (x - 1)), x + 1)
        self.assertEqual(cancel_expression((x**2 - y**2) / (y - x)), -x - y)
        self.assertEqual(cancel_expression((x * y + x) / (x)), y + 1)

    def test_algebra_rejects_functions_float_and_irrational_coefficients(self):
        x = self.x
        for operation in (factor_expression, together_expression, cancel_expression):
            for expression in (
                sp.sin(x),
                x + sp.pi,
                x + sp.sqrt(2),
                x + sp.Float("0.1"),
                sp.sqrt(x),
            ):
                with self.subTest(operation=operation.__name__, expression=expression):
                    self.assertRaises(ValueError, operation, expression)

    def test_factor_does_not_accept_rational_function_as_polynomial(self):
        self.assertRaises(ValueError, factor_expression, 1 / self.x)

    def test_conservative_preflight_prevents_combinatorial_expansion(self):
        variables = sp.symbols("a:9")
        for expression in (sum(variables), self.x**257, sum(variables[:8]) ** 8):
            for operation in (
                factor_expression,
                together_expression,
                cancel_expression,
            ):
                with self.subTest(operation=operation.__name__, expression=expression):
                    self.assertRaises(ValueError, operation, expression)

    def test_preflight_keeps_reasonable_binomial_powers(self):
        expression = (self.x + self.y) ** 20
        self.assertEqual(factor_expression(expression), expression)

    def test_substitute_exact_value_preserves_other_symbols(self):
        x, y = self.x, self.y
        result = substitute_expression(x**2 + y, x, sp.Rational(1, 3))
        self.assertEqual(result, y + sp.Rational(1, 9))
        self.assertFalse(result.has(sp.Float))

    def test_substitute_is_not_recursive_replacement(self):
        x = self.x
        self.assertEqual(substitute_expression(x**2 + 1, x, x + 1), (x + 1) ** 2 + 1)

    def test_substitute_preserves_complex_domain_and_distinct_assumptions(self):
        x = self.x
        self.assertEqual(substitute_expression(sp.sqrt(x**2), x, -sp.Integer(2)), 2)
        self.assertEqual(substitute_expression(sp.sqrt(x**2), x, sp.I), sp.I)
        positive_x = sp.Symbol("x", positive=True)
        self.assertEqual(
            substitute_expression(x + positive_x, x, sp.Integer(2)), positive_x + 2
        )

    def test_substitute_rejects_nonfinite_values_and_results(self):
        self.assertRaises(
            ValueError, substitute_expression, 1 / self.x, self.x, sp.S.Zero
        )
        self.assertRaises(ValueError, substitute_expression, self.x, self.x, sp.oo)
        self.assertRaises(
            ValueError, substitute_expression, self.x, self.x + 1, sp.S.One
        )

    def test_numerical_pi_matches_independent_decimal_reference(self):
        result = numerical(sp.pi, 50)
        reference = sp.Rational("3.14159265358979323846264338327950288419716939937510")
        self.assertIsInstance(result, sp.Float)
        self.assertLess(abs(sp.Rational(result) - reference), sp.Rational(1, 10**49))

    def test_numerical_rational_precision_and_zero_remain_float(self):
        result = numerical(sp.Rational(1, 3), sp.Integer(50))
        self.assertIsInstance(result, sp.Float)
        self.assertLess(
            abs(sp.Rational(result) - sp.Rational(1, 3)), sp.Rational(1, 10**50)
        )
        for exact in (sp.S.Zero, sp.S.One, sp.Integer(-2)):
            with self.subTest(exact=exact):
                self.assertIsInstance(numerical(exact), sp.Float)
        self.assertIsInstance(numerical(sp.Rational(1, 3), 1), sp.Float)
        self.assertGreater(numerical(sp.Rational(1, 3), 1000)._prec, 3000)

    def test_numerical_complex_parts_remain_numeric(self):
        result = numerical(sp.Rational(1, 2) + sp.I * sp.Rational(1, 3), 40)
        real, imaginary = result.as_real_imag()
        self.assertIsInstance(real, sp.Float)
        self.assertIsInstance(imaginary, sp.Float)
        self.assertLess(
            abs(sp.Rational(imaginary) - sp.Rational(1, 3)), sp.Rational(1, 10**40)
        )

    def test_numerical_rejects_precision_types_and_out_of_range(self):
        for precision in (
            0,
            -1,
            1001,
            True,
            False,
            sp.Float(15),
            sp.Rational(3, 2),
            "15",
            self.x,
        ):
            with self.subTest(precision=precision):
                self.assertRaises(ValueError, numerical, sp.pi, precision)

    def test_numerical_rejects_symbolic_and_nonfinite_input(self):
        for expression in (self.x, self.x + 1, sp.oo, -sp.oo, sp.zoo, sp.nan):
            with self.subTest(expression=expression):
                self.assertRaises(ValueError, numerical, expression)

    def test_numerical_precision_exhaustion_is_a_useful_value_error(self):
        identity = sp.sin(1) ** 2 + sp.cos(1) ** 2 - 1
        with self.assertRaisesRegex(ValueError, "precisión solicitada"):
            numerical(identity, 15)
        self.assertEqual(sp.trigsimp(identity), 0)

    def test_all_operations_reject_non_scalar_or_text_without_parsing(self):
        invalid = (
            "x+1",
            "__import__('os')",
            [sp.Integer(1)],
            sp.Matrix([[1]]),
            sp.S.true,
            True,
            1,
        )
        for expression in invalid:
            for operation in (
                factor_expression,
                together_expression,
                cancel_expression,
                numerical,
            ):
                with self.subTest(
                    operation=operation.__name__, expression=repr(expression)
                ):
                    self.assertRaises(ValueError, operation, expression)
            self.assertRaises(
                ValueError, substitute_expression, expression, self.x, sp.S.One
            )


if __name__ == "__main__":
    unittest.main()
