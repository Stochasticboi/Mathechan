"""Known finite relative-entropy optima and numerical convergence contracts."""

import unittest

import sympy as sp

from mathechan.maxent_solver import solve_maxent, solution_diagnostics


class MaxEntSolverTests(unittest.TestCase):
    def assertNear(self, observed, expected, tolerance=sp.Rational(1, 10**40)):
        self.assertLess(abs((observed-expected).evalf(70)), tolerance)

    def test_two_levels_have_exact_probabilities_and_log_multiplier(self):
        result = solve_maxent([0, 1], sp.Rational(1, 4))
        self.assertEqual(result['probabilities'], sp.Tuple(sp.Rational(3, 4), sp.Rational(1, 4)))
        self.assertEqual(sp.simplify(result['multipliers'][0]-sp.log(3)), 0)
        self.assertEqual(result['precision'], 0)
        self.assertEqual(result['iterations'], 0)

    def test_equal_feature_groups_allocate_in_proportion_to_reference(self):
        q = sp.Tuple(sp.Rational(1, 2), sp.Rational(1, 4), sp.Rational(1, 8), sp.Rational(1, 8))
        result = solve_maxent([0, 0, 1, 1], sp.Rational(1, 2), q)
        self.assertEqual(result['probabilities'], sp.Tuple(sp.Rational(1, 3), sp.Rational(1, 6),
                                                          sp.Rational(1, 4), sp.Rational(1, 4)))
        self.assertEqual(result['method'], 'exact_two_groups')

    def test_unique_triangle_uses_constraints_not_an_optimization_tolerance(self):
        result = solve_maxent([[0, 0], [1, 0], [0, 1]], [sp.Rational(1, 4), sp.Rational(1, 4)])
        self.assertEqual(result['probabilities'], sp.Tuple(sp.Rational(1, 2), sp.Rational(1, 4), sp.Rational(1, 4)))
        self.assertEqual(result['method'], 'exact_unique')
        self.assertEqual(result['residuals'], sp.Tuple(0, 0))

    def test_feasible_reference_is_the_exact_zero_kl_solution(self):
        q = sp.Tuple(sp.Rational(1, 2), sp.Rational(1, 3), sp.Rational(1, 6))
        result = solve_maxent([0, 1, 2], sp.Rational(2, 3), q)
        self.assertEqual(result['probabilities'], q)
        self.assertEqual(result['multipliers'], sp.Tuple(0))
        self.assertEqual(result['dual_gap'], 0)

    def test_three_levels_match_independent_quadratic_root_solution(self):
        result = solve_maxent([0, 1, 2], sp.Rational(1, 2), precision=50)
        ratio = (sp.sqrt(13)-1)/6
        expected = (1, ratio, ratio**2)
        total = sum(expected)
        for value, weight in zip(result['probabilities'], expected):
            self.assertNear(value, weight/total)
        self.assertNear(result['multipliers'][0], -sp.log(ratio))
        self.assertEqual(result['method'], 'damped_newton')
        self.assertEqual(sum(result['probabilities']), 1)
        self.assertTrue(all(value > 0 for value in result['probabilities']))

    def test_two_observables_match_independent_product_distribution(self):
        result = solve_maxent([[0, 0], [0, 1], [1, 0], [1, 1]],
                              [sp.Rational(1, 3), sp.Rational(1, 4)], precision=50)
        for value, expected in zip(result['probabilities'],
                                   (sp.Rational(1, 2), sp.Rational(1, 6), sp.Rational(1, 4), sp.Rational(1, 12))):
            self.assertNear(value, expected)
        for value, expected in zip(result['multipliers'], (sp.log(2), sp.log(3))):
            self.assertNear(value, expected)
        self.assertLess(result['stationarity_residual'], sp.Rational(1, 10**40))

    def test_boundary_is_solved_on_its_relative_face(self):
        result = solve_maxent([[0, 0], [0, 1], [1, 0], [1, 1]], [0, sp.Rational(1, 3)])
        self.assertEqual(result['probabilities'], sp.Tuple(sp.Rational(2, 3), sp.Rational(1, 3), 0, 0))
        self.assertTrue(result['boundary'])
        self.assertEqual(result['support'], sp.Tuple(0, 1))
        self.assertEqual(result['basis'], sp.Tuple(1))
        self.assertEqual(result['multipliers'][0], 0)  # Gauge on the face, not a finite global dual.
        self.assertTrue(result['face_certificate'])

    def test_zero_reference_excludes_states_without_a_false_boundary_flag(self):
        result = solve_maxent([0, 1, 2], sp.Rational(3, 2), [0, sp.Rational(1, 2), sp.Rational(1, 2)])
        self.assertEqual(result['probabilities'], sp.Tuple(0, sp.Rational(1, 2), sp.Rational(1, 2)))
        self.assertFalse(result['boundary'])
        self.assertEqual(result['support'], sp.Tuple(1, 2))

    def test_redundant_observables_use_a_declared_multiplier_gauge(self):
        result = solve_maxent([[0, 0], [1, 2]], [sp.Rational(1, 3), sp.Rational(2, 3)])
        self.assertEqual(result['rank'], 1)
        self.assertEqual(result['basis'], sp.Tuple(0))
        self.assertEqual(result['multipliers'][1], 0)
        self.assertEqual(sp.simplify(result['multipliers'][0]-sp.log(2)), 0)

    def test_centering_preserves_large_offset_and_small_feature_units(self):
        base = solve_maxent([0, 1, 2], sp.Rational(1, 2))
        shift = sp.Integer(10)**30
        shifted = solve_maxent([shift, shift+1, shift+2], shift+sp.Rational(1, 2))
        tiny = sp.Rational(1, 10**100)
        scaled = solve_maxent([0, tiny, 2*tiny], tiny/2)
        for reference, a, b in zip(base['probabilities'], shifted['probabilities'], scaled['probabilities']):
            self.assertNear(a, reference)
            self.assertNear(b, reference)

    def test_exact_large_offset_keeps_log_partition_as_a_compact_sum(self):
        shift = sp.Integer(10)**30
        result = solve_maxent([shift, shift+1], shift+sp.Rational(1, 4))
        self.assertEqual(result['probabilities'], sp.Tuple(sp.Rational(3, 4), sp.Rational(1, 4)))
        self.assertEqual(result['logz'], -sp.log(sp.Rational(3, 2))-shift*sp.log(3))
        self.assertLess(sp.count_ops(result['logz']), 10)

    def test_exact_tiny_units_do_not_exponentiate_a_large_multiplier(self):
        unit = sp.Rational(1, 10**100)
        result = solve_maxent([0, unit], unit/4)
        self.assertEqual(result['multipliers'], sp.Tuple(sp.log(3)/unit))
        self.assertEqual(result['stationarity_residual'], 0)
        self.assertEqual(result['probabilities'], sp.Tuple(sp.Rational(3, 4), sp.Rational(1, 4)))

    def test_near_boundary_mean_has_relative_accuracy_not_only_absolute_residual(self):
        target = sp.Rational(1, 10**30)
        result = solve_maxent([0, 1, 2], target)
        observed = result['probabilities'][1]+2*result['probabilities'][2]
        self.assertLess(abs((observed/target-1).evalf(80)), sp.Rational(1, 10**40))
        self.assertTrue(all(value > 0 for value in result['probabilities']))
        self.assertFalse(result['boundary'])

    def test_infeasible_and_invalid_requests_never_return_a_fallback_distribution(self):
        for f, target in (([0, 1], 2), ([[0, 0], [1, 0], [0, 1]], [sp.Rational(3, 4), sp.Rational(3, 4)])):
            with self.assertRaises(ValueError):
                solve_maxent(f, target)
        for digits in (True, 9, 101, sp.Rational(1, 2)):
            with self.assertRaises(ValueError):
                solve_maxent([0, 1], sp.Rational(1, 2), precision=digits)

    def test_diagnostic_validation_rejects_perturbed_stationarity(self):
        f = sp.Tuple(sp.Tuple(0), sp.Tuple(1), sp.Tuple(2))
        q = sp.Tuple(sp.Rational(1, 3), sp.Rational(1, 3), sp.Rational(1, 3))
        with self.assertRaises(ValueError):
            solution_diagnostics(f, sp.Tuple(sp.Rational(1, 4)), q,
                                 sp.Tuple(sp.Rational(3, 4), sp.Rational(1, 4), 0), sp.Tuple(0), (0, 1), 50)


if __name__ == '__main__':
    unittest.main()
