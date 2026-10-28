"""Finite convex moment geometry, including exact boundary certificates."""

import unittest
from unittest.mock import patch

import sympy as sp

from mathechan.maxent_geometry import (
    prepare_problem, normalize_problem, InfeasibleMomentsError, GeometryBudgetError,
)


class MaxEntGeometryTests(unittest.TestCase):
    def assert_certificate(self, problem):
        rows, targets, prior = problem['features'], problem['targets'], problem['reference']
        witness, exposure = problem['feasible'], problem['face_certificate']
        active = set(problem['support'])
        self.assertEqual(sum(witness), 1)
        self.assertEqual(sum(exposure[j+1]*targets[j] for j in range(len(targets)))+exposure[0], 0)
        for column, target in enumerate(targets):
            self.assertEqual(sum(p*row[column] for p, row in zip(witness, rows)), target)
        for index, (row, mass) in enumerate(zip(rows, prior)):
            self.assertEqual(witness[index] > 0, index in active)
            if mass == 0:
                self.assertEqual(witness[index], 0)
                continue
            value = exposure[0]+sum(coefficient*feature for coefficient, feature in zip(exposure[1:], row))
            if index in active:
                self.assertEqual(value, 0)
            else:
                self.assertGreaterEqual(value, 1)

    def test_two_state_unique_distribution(self):
        result = prepare_problem([0, 1], sp.Rational(1, 4))
        self.assertEqual(result['feasible'], sp.Tuple(sp.Rational(3, 4), sp.Rational(1, 4)))
        self.assertEqual(result['support'], (0, 1))
        self.assertEqual(result['basis'], (0,))
        self.assertFalse(result['boundary'])
        self.assert_certificate(result)

    def test_multivariate_convex_hull_not_coordinatewise_bounds(self):
        # Both means lie in [0,1], but x+y cannot exceed one in this triangle.
        with self.assertRaises(InfeasibleMomentsError):
            prepare_problem([[0, 0], [1, 0], [0, 1]], [sp.Rational(3, 4)]*2)
        with self.assertRaises(InfeasibleMomentsError):
            prepare_problem([[0, 0], [1, 0], [0, 1], [sp.Rational(1, 4), sp.Rational(1, 4)]],
                            [sp.Rational(3, 4)]*2)

    def test_boundary_square_face_and_rank(self):
        result = prepare_problem([[0, 0], [1, 0], [0, 1], [1, 1]], [0, sp.Rational(1, 2)])
        self.assertEqual(result['support'], (0, 2))
        self.assertEqual(result['basis'], (1,))
        self.assertEqual(result['rank'], 1)
        self.assertTrue(result['boundary'])
        self.assert_certificate(result)

    def test_redundant_constraints_and_inconsistent_targets(self):
        result = prepare_problem([[0, 0], [1, 2], [2, 4]], [1, 2])
        self.assertEqual(result['basis'], (0,))
        self.assertEqual(result['rank'], 1)
        self.assert_certificate(result)
        with self.assertRaises(InfeasibleMomentsError):
            prepare_problem([[0, 0], [1, 2], [2, 4]], [1, 3])

    def test_duplicate_observable_rows_are_distinct_states(self):
        result = prepare_problem([0, 0, 1], sp.Rational(1, 2))
        self.assertEqual(result['support'], (0, 1, 2))
        self.assert_certificate(result)

    def test_reference_zeros_define_allowed_support(self):
        result = prepare_problem([0, 1, 2], 1, [0, 1, 0])
        self.assertEqual(result['support'], (1,))
        self.assertFalse(result['boundary'])
        self.assertEqual(result['rank'], 0)
        self.assert_certificate(result)
        with self.assertRaises(InfeasibleMomentsError):
            prepare_problem([0, 1, 2], 0, [0, 1, 0])

    def test_tiny_positive_mean_is_not_boundary(self):
        result = prepare_problem([0, 1, 2], sp.Rational(1, 10**100))
        self.assertEqual(result['support'], (0, 1, 2))
        self.assertFalse(result['boundary'])
        self.assert_certificate(result)

    def test_endpoint_and_one_state(self):
        for features, target, expected in (([0, 1, 2], 0, (0,)),
                                            ([0, 1, 2], 2, (2,)), ([7], 7, (0,))):
            result = prepare_problem(features, target)
            self.assertEqual(result['support'], expected)
            self.assertEqual(result['rank'], 0)
            self.assert_certificate(result)

    def test_float_data_are_exact_stored_binary_values(self):
        result = prepare_problem([0., 1.], sp.Float('0.1'))
        self.assertTrue(result['input_approximate'])
        self.assertEqual(result['targets'][0], sp.Rational(sp.Float('0.1')))
        self.assert_certificate(result)

    def test_normalize_does_not_run_lp(self):
        with patch('mathechan.maxent_geometry.linprog', side_effect=AssertionError('LP invoked')):
            result = normalize_problem([[0], [1]], [sp.Rational(1, 2)])
        self.assertEqual(result['reference'], sp.Tuple(sp.Rational(1, 2), sp.Rational(1, 2)))

    def test_invalid_domains_shapes_and_budgets(self):
        invalid = (([], 0, None), ([0]*33, 0, None), ([[0]*5], [0]*5, None),
                   ([[0, 1], [2]], [0, 1], None), ([0, 1], [0, 1], None),
                   ([0, 1], 0, [1, 1]), ([0, 1], 0, [-1, 2]),
                   ([0, 1], 0, [0, 0]), ([sp.pi, 1], 0, None),
                   ([sp.Symbol('x'), 1], 0, None), ([True, 1], 0, None),
                   ([sp.I, 1], 0, None), ([float('nan'), 1], 0, None),
                   ([2**4096, 1], 0, None), (["__import__('os')", 1], 0, None))
        for features, targets, reference in invalid:
            with self.subTest(features=features), self.assertRaises(ValueError):
                prepare_problem(features, targets, reference)

    def test_lp_failure_uses_exact_fallback_and_expositor(self):
        with patch('mathechan.maxent_geometry.linprog', side_effect=ValueError('backend unavailable')):
            result = prepare_problem([0, 1, 2], 0)
            interior = prepare_problem([0, 1, 2], 1)
            with self.assertRaises(InfeasibleMomentsError):
                prepare_problem([0, 1, 2], 4)
        self.assert_certificate(result)
        self.assert_certificate(interior)

    def test_invalid_lp_witness_cannot_be_used(self):
        with patch('mathechan.maxent_geometry.linprog', return_value=(0, [0, 0, 1])):
            result = prepare_problem([0, 1, 2], 1)
        self.assert_certificate(result)
        self.assertEqual(result['support'], (0, 1, 2))

    def test_exhausted_search_is_not_labeled_infeasible(self):
        with patch('mathechan.maxent_geometry.linprog', side_effect=ValueError('backend unavailable')), \
             patch('mathechan.maxent_geometry.MAX_BASES', 1):
            with self.assertRaises(GeometryBudgetError):
                prepare_problem([0, 1, 2], sp.Rational(3, 2))


if __name__ == '__main__':
    unittest.main()
