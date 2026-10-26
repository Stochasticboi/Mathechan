"""Exact level references and extreme-temperature numerical regressions."""

import unittest

import sympy as sp

from mathechan.canonical_numeric import canonical_numeric_values
from mathechan.finite_probability import FiniteDistribution


def values(energies, beta, degeneracies=None, precision=50):
    if degeneracies is None:
        degeneracies = (1,)*len(energies)
    return canonical_numeric_values(energies, beta, degeneracies, precision)


class CanonicalNumericTests(unittest.TestCase):
    def assert_close(self, actual, expected, absolute=sp.Rational(1, 10**45)):
        self.assertLess(abs((actual-expected).evalf(100)), absolute)

    def assert_relative(self, actual, expected, relative=sp.Rational(1, 10**45)):
        self.assertLess(abs((actual/expected-1).evalf(100)), relative)

    def test_zero_beta_counts_microstates(self):
        result = values((0, 1, 2), 0, (1, 2, 1))
        self.assertEqual(result['probabilities'], sp.Tuple(sp.Rational(1, 4), sp.Rational(1, 2), sp.Rational(1, 4)))
        self.assert_close(result['energy'], 1)
        self.assert_close(result['variance'], sp.Rational(1, 2))
        self.assert_close(result['entropy'], sp.log(4))
        self.assert_close(result['logz'], sp.log(4))
        self.assertEqual(result['heat_capacity'], 0)
        self.assertIsNone(result['free_energy'])

    def test_three_level_binomial_spectrum_exact_reference(self):
        result = values((0, 1, 2), sp.log(2), (1, 2, 1))
        self.assertEqual(result['probabilities'], sp.Tuple(sp.Rational(4, 9), sp.Rational(4, 9), sp.Rational(1, 9)))
        self.assert_close(result['energy'], sp.Rational(2, 3))
        self.assert_close(result['variance'], sp.Rational(4, 9))
        self.assert_close(result['logz'], sp.log(sp.Rational(9, 4)))
        self.assert_close(result['entropy'], 2*sp.log(3)-sp.Rational(4, 3)*sp.log(2))
        self.assert_close(result['free_energy'], -sp.log(sp.Rational(9, 4))/sp.log(2))
        self.assert_close(result['heat_capacity'], sp.Rational(4, 9)*sp.log(2)**2)

    def test_positive_large_beta_retains_rare_state_and_small_entropy(self):
        result = values((0, 1), 1000)
        tiny = sp.exp(-1000)
        self.assertGreater(result['probabilities'][1], 0)
        self.assertEqual(sum(result['probabilities']), 1)
        self.assert_relative(result['probabilities'][1], tiny)
        self.assert_relative(result['variance'], tiny)
        self.assert_relative(result['entropy'], 1001*tiny)
        self.assert_relative(result['logz'], tiny)
        self.assert_relative(result['heat_capacity'], 10**6*tiny)

    def test_negative_large_beta_retains_low_energy_tail(self):
        result = values((0, 1), -1000)
        tiny = sp.exp(-1000)
        self.assertGreater(result['probabilities'][0], 0)
        self.assert_relative(result['probabilities'][0], tiny)
        self.assert_relative(result['variance'], tiny)
        self.assert_relative(result['entropy'], 1001*tiny)
        self.assert_close(result['logz'], 1000)

    def test_energy_shift_does_not_destroy_variance(self):
        offset, beta = sp.Integer(10)**30, sp.log(3)
        base = values((0, 1), beta, precision=100)
        shifted = values((offset, offset+1), beta, precision=100)
        self.assertEqual(base['probabilities'], shifted['probabilities'])
        self.assert_close(shifted['variance'], sp.Rational(3, 16), sp.Rational(1, 10**90))
        self.assert_close(shifted['entropy'], base['entropy'], sp.Rational(1, 10**90))
        self.assert_close(shifted['energy'], offset+sp.Rational(1, 4), sp.Rational(1, 10**65))
        self.assert_close(shifted['logz']+beta*offset, base['logz'], sp.Rational(1, 10**65))
        self.assert_close(shifted['free_energy']-offset, base['free_energy'], sp.Rational(1, 10**65))

    def test_float_offsets_use_stored_values_before_centering(self):
        offset = sp.Float(10**30, 60)
        result = values((offset, offset+1), 0)
        self.assert_close(result['variance'], sp.Rational(1, 4))
        self.assert_close(result['energy'], sp.Integer(10)**30+sp.Rational(1, 2), sp.Rational(1, 10**15))

    def test_equal_energies_have_no_exponential_dynamic_range(self):
        offset = sp.Integer(10)**100
        result = values((offset, offset), 1000, (2, 3))
        self.assertEqual(result['probabilities'], sp.Tuple(sp.Rational(2, 5), sp.Rational(3, 5)))
        self.assertEqual(result['variance'], 0)
        self.assert_close(result['entropy'], sp.log(5))

    def test_exact_normalization_accepts_existing_distribution_contract(self):
        result = values((-3, 0, 2), sp.Rational(7, 11), (1, 3, 2))
        distribution = FiniteDistribution((1, 2, 3), result['probabilities'])
        self.assertEqual(sum(distribution.probabilities), 1)
        self.assertTrue(all(item > 0 for item in distribution.probabilities))
        self.assertEqual(result['diagnostics']['normalization_residual'], '0')
        self.assertIs(result['diagnostics']['precision_certified'], False)

    def test_unresolved_input_and_invalid_arguments_are_rejected(self):
        cases = (
            ((0, 1), sp.Symbol('beta'), (1, 1), 50),
            ((0, 1), sp.oo, (1, 1), 50),
            ((0, sp.I), 1, (1, 1), 50),
            ((0, 1), 1, (1, 0), 50),
            ((0, 1), 1, (1, sp.Float(2)), 50),
            ((0, 1), 1, (1,), 50),
            ((), 1, (), 50),
            ((0, 1), 1, (1, 1), 9),
            ((0, 1), 1, (1, 1), 201),
            ((0, 1), 1, (1, 1), sp.Float(50)),
            ((0, 1), True, (1, 1), 50),
        )
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                canonical_numeric_values(*args)

    def test_resource_limits_reject_without_dropping_tails(self):
        with self.assertRaisesRegex(ValueError, '6000'):
            values((0, 1), 6001)
        with self.assertRaisesRegex(ValueError, '12000'):
            count = sp.Integer(2)**13000
            values((0, 1), 0, (count, count+1))
        with self.assertRaisesRegex(ValueError, '16384'):
            values((0, sp.Integer(2)**17000), 0)


if __name__ == '__main__':
    unittest.main()
