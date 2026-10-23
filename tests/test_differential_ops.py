"""Exact reference cases for formal partial and Cartesian derivatives."""

import unittest

import sympy as sp

from mathechan.differential_ops import derivative_expression, vector_expression


class DifferentialOperationsTests(unittest.TestCase):
    def setUp(self):
        self.x, self.y, self.z, self.a = sp.symbols("x y z a")

    def test_higher_derivatives_preserve_parameters(self):
        x, a = self.x, self.a
        outcome = derivative_expression(a * x**5 + sp.sin(x), ((x, 3),))
        self.assertEqual(outcome.value, 60 * a * x**2 - sp.cos(x))
        self.assertEqual(outcome.details["orders"], [3])

    def test_mixed_partial_with_special_function(self):
        x, y = self.x, self.y
        result = derivative_expression(x**3*y**2 + sp.gamma(x), ((x, 2), (y, 1)))
        self.assertEqual(result.value, 12*x*y)

    def test_undefined_function_stays_unresolved(self):
        x = self.x
        result = derivative_expression(sp.Function("f")(x), ((x, 1),))
        self.assertEqual(result.status, "unresolved")
        self.assertEqual(result.value, sp.Derivative(sp.Function("f")(x), x))

    def test_abs_does_not_silently_assume_real(self):
        x = self.x
        result = derivative_expression(sp.Abs(x), ((x, 1),))
        self.assertTrue(result.value.has(sp.Derivative))
        self.assertIsNone(x.is_real)
        self.assertEqual(result.details["differentiability"], "not_certified")

    def test_scalar_gradient_of_harmonic_potential(self):
        x, y, z, a = self.x, self.y, self.z, self.a
        result = vector_expression("Grad", a*(x*x+y*y+z*z)/2, [x, y, z])
        self.assertEqual(result.value, sp.ImmutableMatrix([a*x, a*y, a*z]))
        self.assertEqual(result.details["coordinates"], "Cartesian")

    def test_divergence_quadratic_field(self):
        x, y, z = self.x, self.y, self.z
        self.assertEqual(vector_expression("Div", [x*x, y*y, z*z], [x, y, z]).value,
                         2*(x+y+z))

    def test_curl_orientation(self):
        x, y, z = self.x, self.y, self.z
        result = vector_expression("Curl", [-y/2, x/2, 0*sp.S.One], [x, y, z])
        self.assertEqual(result.value, sp.ImmutableMatrix([0, 0, 1]))

    def test_curl_of_gradient_zero(self):
        x, y, z = self.x, self.y, self.z
        gradient = vector_expression("Grad", x*y*z, [x, y, z]).value
        self.assertEqual(vector_expression("Curl", gradient, [x, y, z]).value,
                         sp.ImmutableMatrix([0, 0, 0]))

    def test_rectangular_jacobian(self):
        x, y, z = self.x, self.y, self.z
        result = vector_expression("Jacobian", sp.Tuple(x*y, y*z), [x, y, z])
        self.assertEqual(result.value, sp.ImmutableMatrix([[y, x, 0], [0, z, y]]))

    def test_hessian_symmetric(self):
        x, y = self.x, self.y
        result = vector_expression("Hessian", x*x*y+sp.exp(y), [x, y]).value
        self.assertEqual(result, sp.ImmutableMatrix([[2*y, 2*x], [2*x, sp.exp(y)]]))
        self.assertEqual(result, result.T)

    def test_invalid_order_and_total(self):
        x, y = self.x, self.y
        for specs in [(), ((x, 0),), ((x, -1),), ((x, 33),), ((x, True),),
                      ((x, sp.Rational(1, 2)),), ((x, 20), (y, 20))]:
            with self.subTest(specs=specs), self.assertRaises(ValueError):
                derivative_expression(x*y, specs)

    def test_dimension_and_scalar_validation(self):
        x, y, z = self.x, self.y, self.z
        cases = [("Curl", [x, y], [x, y]), ("Div", [x], [x, y]),
                 ("Grad", [x,y], [x]), ("Hessian", sp.Eq(x, 0), [x]),
                 ("Jacobian", sp.Matrix([[x, y]]), [x, y]),
                 ("Grad", x, [x, x]), ("Grad", x, []),
                 ("Grad", x, [sp.Integer(1)]), ("Other", x, [x])]
        for operation, expression, variables in cases:
            with self.subTest(operation=operation, expression=expression), self.assertRaises(ValueError):
                vector_expression(operation, expression, variables)

    def test_symbol_and_operation_budget(self):
        symbols = sp.symbols("x0:9")
        with self.assertRaises(ValueError):
            derivative_expression(sum(symbols), ((symbols[0], 1),))
        expression = sum(sp.sin(self.x + index) for index in range(150))
        with self.assertRaises(ValueError):
            vector_expression("Grad", expression, [self.x])

    def test_eight_dimensional_hessian_has_64_elements(self):
        variables = sp.symbols("x0:8")
        result = vector_expression("Hessian", sum(x*x for x in variables), variables).value
        self.assertEqual(result, 2*sp.eye(8))
        self.assertIsInstance(result, sp.ImmutableMatrix)

    def test_nonfinite_input_rejected(self):
        for value in [sp.oo, sp.zoo, sp.nan, sp.Eq(self.x, 0)]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                derivative_expression(value, ((self.x, 1),))


if __name__ == "__main__":
    unittest.main()
