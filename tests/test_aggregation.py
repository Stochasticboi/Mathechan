"""Regression tests for integer-range and convergence semantics."""

import unittest

import sympy as sp

from mathechan.aggregation import aggregate_expression


class AggregationTests(unittest.TestCase):
    def setUp(self):
        self.i, self.j, self.n = sp.symbols("i j n", integer=True)

    def test_finite_sum(self):
        result = aggregate_expression(self.i**2, ((self.i, 1, 10),))
        self.assertEqual(result.value, 385)
        self.assertEqual(result.status, "evaluated")

    def test_empty_ranges_do_not_use_karr_convention(self):
        for operation, identity in (("Sum", 0), ("Product", 1)):
            self.assertEqual(aggregate_expression(self.i, ((self.i, 5, 1),), operation).value, identity)

    def test_finite_product(self):
        result = aggregate_expression(self.i, ((self.i, 1, 7),), "Product")
        self.assertEqual(result.value, sp.factorial(7))

    def test_dependent_inner_bounds_and_order(self):
        result = aggregate_expression(self.j, ((self.i, 1, 3), (self.j, 1, self.i)))
        self.assertEqual(result.value, 10)

    def test_dependent_empty_inner_range(self):
        result = aggregate_expression(self.j, ((self.i, 1, 3), (self.j, 2, self.i)))
        self.assertEqual(result.value, 7)

    def test_symbolic_sum_preserves_empty_branch(self):
        result = aggregate_expression(self.i, ((self.i, 1, self.n),))
        self.assertEqual(result.value.subs(self.n, -3), 0)
        self.assertEqual(result.value.subs(self.n, 4), 10)

    def test_symbolic_factorial_product(self):
        result = aggregate_expression(self.i, ((self.i, 1, self.n),), "Product")
        self.assertEqual(result.value.subs(self.n, 5), 120)
        self.assertEqual(result.value.subs(self.n, -2), 1)

    def test_unknown_integrality_is_an_explicit_requirement(self):
        n = sp.Symbol("n")
        result = aggregate_expression(self.i, ((self.i, 1, n),))
        self.assertIn("Contains(n, Integers)", result.conditions)
        self.assertEqual(result.status, "conditional")

    def test_outer_integer_scope_does_not_escape(self):
        i, j, n = sp.symbols("i j n")
        result = aggregate_expression(j, ((i, 1, n), (j, 1, i)))
        self.assertIn("Contains(n, Integers)", result.conditions)
        self.assertNotIn("Contains(i, Integers)", result.conditions)
        self.assertIsNone(i.is_integer)

    def test_affine_integer_inner_bound_is_valid_without_free_index_condition(self):
        i, j = sp.symbols("i j")
        result = aggregate_expression(j, ((i, 1, 3), (j, 1, 2*i+1)))
        self.assertEqual(result.value, 49)
        self.assertEqual(result.conditions, ())

    def test_undecidable_dependent_bound_stays_inert(self):
        i, j, n = sp.symbols("i j n")
        for upper in (i/2, i+n):
            with self.subTest(upper=upper):
                result = aggregate_expression(j, ((i, 1, n), (j, 1, upper)))
                self.assertEqual(result.status, "unresolved")
                self.assertIsInstance(result.value, sp.Sum)
                self.assertEqual(result.conditions, ("Contains(n, Integers)",))

    def test_noninteger_dependent_bound_rejected(self):
        i, j = sp.symbols("i j")
        with self.assertRaises(ValueError):
            aggregate_expression(j, ((i, 1, 3), (j, 1, i+sp.Rational(1, 2))))

    def test_noninteger_bound_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_expression(self.i, ((self.i, 1, sp.Rational(3, 2)),))

    def test_geometric_sum_preserves_convergence_branch(self):
        q = sp.Symbol("q")
        result = aggregate_expression(q**self.i, ((self.i, 0, sp.oo),))
        self.assertEqual(result.status, "conditional")
        self.assertEqual(result.value.subs(q, sp.Rational(1, 2)), 2)
        self.assertTrue(result.value.subs(q, 2).has(sp.Sum))

    def test_convergent_infinite_sum(self):
        result = aggregate_expression(1 / self.i**2, ((self.i, 1, sp.oo),))
        self.assertEqual(result.value, sp.pi**2 / 6)
        self.assertEqual(result.status, "evaluated")

    def test_harmonic_divergence_is_held(self):
        result = aggregate_expression(1 / self.i, ((self.i, 1, sp.oo),))
        self.assertEqual(result.status, "divergent")
        self.assertIsInstance(result.value, sp.Sum)

    def test_oscillation_is_not_a_scalar(self):
        result = aggregate_expression((-1)**self.i, ((self.i, 0, sp.oo),))
        self.assertEqual(result.status, "divergent")
        self.assertIsInstance(result.value, sp.Sum)

    def test_zero_infinite_product_not_claimed_convergent(self):
        result = aggregate_expression(sp.Rational(1, 2), ((self.i, 1, sp.oo),), "Product")
        self.assertEqual(result.status, "divergent")
        self.assertIsInstance(result.value, sp.Product)

    def test_lower_infinite_bound(self):
        result = aggregate_expression(2**self.i, ((self.i, -sp.oo, 0),))
        self.assertEqual(result.value, 2)

    def test_no_repeated_indices(self):
        with self.assertRaises(ValueError):
            aggregate_expression(self.i, ((self.i, 1, 2), (self.i, 1, 2)))

    def test_outer_bounds_cannot_reference_inner_index(self):
        with self.assertRaises(ValueError):
            aggregate_expression(self.i, ((self.i, 1, self.j), (self.j, 1, 2)))

    def test_finite_range_budget(self):
        with self.assertRaises(ValueError):
            aggregate_expression(self.i, ((self.i, 1, 1001),))

    def test_total_budget_nested(self):
        with self.assertRaises(ValueError):
            aggregate_expression(self.i * self.j, ((self.i, 1, 50), (self.j, 1, 50)))

    def test_finite_singular_term_is_not_scalar(self):
        result = aggregate_expression(1 / self.i, ((self.i, -1, 1),))
        self.assertEqual(result.status, "unresolved")
        self.assertIsInstance(result.value, sp.Sum)

    def test_empty_symbolic_outer_range_does_not_evaluate_divergent_inner(self):
        result = aggregate_expression(1 / self.j,
                                      ((self.i, self.n, self.n - 2), (self.j, 1, sp.oo)))
        self.assertEqual(result.value, 0)
        self.assertEqual(result.status, "evaluated")

    def test_float_integer_looking_bound_is_not_exact(self):
        with self.assertRaises(ValueError):
            aggregate_expression(self.i, ((self.i, 1, sp.Float(3)),))

    def test_three_ranges(self):
        k = sp.Symbol("k", integer=True)
        result = aggregate_expression(self.i + self.j + k,
                                      ((self.i, 1, 2), (self.j, 1, 2), (k, 1, 2)))
        self.assertEqual(result.value, 36)

    def test_bound_input_is_not_parsed_as_source(self):
        with self.assertRaises(ValueError):
            aggregate_expression(self.i, ((self.i, "1", "4"),))


if __name__ == "__main__":
    unittest.main()
