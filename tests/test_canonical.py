"""Exact finite ensembles, microstate entropy and limiting thermal identities."""

import unittest
from unittest.mock import patch

import sympy as sp

from mathechan.canonical import CanonicalState, canonical_operation, canonical_requirements


def query(name, state):
    return canonical_operation(name, (state,))[0].value


class CanonicalTests(unittest.TestCase):
    def test_state_constructor_stores_data_without_computing_an_ensemble(self):
        with patch('mathechan.canonical._exact_values', side_effect=AssertionError('calculation')):
            state = CanonicalState((0, 1), sp.Symbol('b'))
            rebuilt = CanonicalState(*state.args)
        self.assertEqual(state, rebuilt)
        self.assertEqual(state.degeneracies, sp.Tuple(1, 1))
        self.assertEqual(state.precision, 0)

    def test_zero_beta_weights_levels_by_degeneracy(self):
        state = CanonicalState((0, 1, 2), sp.S.Zero, (1, 2, 1))
        self.assertEqual(query('Probabilities', state), sp.Tuple(sp.Rational(1, 4), sp.Rational(1, 2), sp.Rational(1, 4)))
        self.assertEqual(query('LogZ', state), sp.log(4))
        self.assertEqual(query('Energy', state), 1)
        self.assertEqual(query('Variance', state), sp.Rational(1, 2))
        self.assertEqual(query('Entropy', state), sp.log(4))
        self.assertEqual(query('HeatCapacity', state), 0)

    def test_three_level_exact_reference(self):
        state = CanonicalState((0, 1, 2), sp.log(2), (1, 2, 1))
        self.assertEqual(query('Probabilities', state), sp.Tuple(sp.Rational(4, 9), sp.Rational(4, 9), sp.Rational(1, 9)))
        self.assertEqual(query('LogZ', state), sp.log(sp.Rational(9, 4)))
        self.assertEqual(query('Energy', state), sp.Rational(2, 3))
        self.assertEqual(query('Variance', state), sp.Rational(4, 9))
        self.assertEqual(sp.simplify(query('HeatCapacity', state)-4*sp.log(2)**2/9), 0)

    def test_microstate_entropy_differs_from_level_shannon_entropy(self):
        state = CanonicalState((0, 1, 2), sp.S.Zero, (1, 2, 1))
        probabilities = query('Probabilities', state)
        level_entropy = -sum(p*sp.log(p) for p in probabilities)
        self.assertEqual(sp.simplify(level_entropy), 3*sp.log(2)/2)
        microstate = level_entropy+sum(p*sp.log(g) for p, g in zip(probabilities, state.degeneracies))
        self.assertEqual(sp.simplify(microstate-query('Entropy', state)), 0)

    def test_dist_uses_level_indices_not_repeated_energies(self):
        state = CanonicalState((1, 1), sp.Integer(3))
        distribution = query('Dist', state)
        self.assertEqual(distribution.states, sp.Tuple(1, 2))
        self.assertEqual(distribution.probabilities, sp.Tuple(sp.Rational(1, 2), sp.Rational(1, 2)))
        self.assertEqual(query('Entropy', state), sp.log(2))

    def test_changing_energy_zero_preserves_probabilities_entropy_and_variance(self):
        beta, shift = sp.symbols('b c', real=True)
        original = CanonicalState((0, 1), beta, (1, 3))
        shifted = CanonicalState((shift, shift+1), beta, (1, 3))
        for operation in ('Probabilities', 'Entropy', 'Variance', 'HeatCapacity'):
            before, after = query(operation, original), query(operation, shifted)
            self.assertEqual(before, after)
        for operation in ('Energy', 'FreeEnergy'):
            self.assertEqual(sp.simplify(query(operation, shifted)-query(operation, original)-shift), 0)
        self.assertEqual(sp.simplify(query('LogZ', shifted)-query('LogZ', original)+beta*shift), 0)

    def test_log_partition_derivatives_and_thermal_fluctuation_identity(self):
        beta = sp.Symbol('b', real=True)
        state = CanonicalState((0, 1), beta, (1, 2))
        logz, energy, variance = (query(operation, state) for operation in ('LogZ', 'Energy', 'Variance'))
        self.assertEqual(sp.simplify(sp.diff(logz, beta)+energy), 0)
        self.assertEqual(sp.simplify(sp.diff(logz, beta, 2)-variance), 0)
        self.assertEqual(sp.simplify(sp.diff(query('Entropy', state), beta)+beta*variance), 0)

    def test_signed_beta_reverses_populations_in_two_level_spectrum(self):
        positive = CanonicalState((0, 1), sp.log(3))
        negative = CanonicalState((0, 1), -sp.log(3))
        self.assertEqual(query('Probabilities', positive), sp.Tuple(sp.Rational(3, 4), sp.Rational(1, 4)))
        self.assertEqual(query('Probabilities', negative), sp.Tuple(sp.Rational(1, 4), sp.Rational(3, 4)))

    def test_infinite_beta_limits_retain_extreme_degeneracy(self):
        cold = CanonicalState((1, 1, 2), sp.oo, (1, 2, 10))
        inverted = CanonicalState((1, 1, 2), -sp.oo, (1, 2, 10))
        self.assertEqual(query('Probabilities', cold), sp.Tuple(sp.Rational(1, 3), sp.Rational(2, 3), 0))
        self.assertEqual(query('Probabilities', inverted), sp.Tuple(0, 0, 1))
        self.assertEqual(query('Entropy', cold), sp.log(3))
        self.assertEqual(query('Entropy', inverted), sp.log(10))
        for state, extreme in ((cold, 1), (inverted, 2)):
            self.assertEqual(query('Energy', state), extreme)
            self.assertEqual(query('FreeEnergy', state), extreme)
            self.assertEqual(query('Variance', state), 0)
            self.assertEqual(query('HeatCapacity', state), 0)
            with self.assertRaises(ValueError):
                query('LogZ', state)
        self.assertEqual(query('LogZ', CanonicalState((0, 0), sp.oo, (1, 2))), sp.log(3))

    def test_zero_beta_free_energy_is_rejected_even_when_algebra_cancels_it(self):
        for energies in ((0, 1), (7,)):
            with self.subTest(energies=energies), self.assertRaises(ValueError):
                query('FreeEnergy', CanonicalState(energies, sp.S.Zero))

    def test_symbolic_domains_remain_after_observables_eliminate_parameters(self):
        energy, degeneracy = sp.symbols('e g')
        state = CanonicalState((energy,), sp.S.Zero, (degeneracy,))
        outcome, requirements = canonical_operation('Entropy', (state,))
        self.assertEqual(outcome.value, sp.log(degeneracy))
        self.assertIn(sp.Contains(energy, sp.S.Reals), requirements)
        self.assertIn(sp.Contains(degeneracy, sp.S.Integers), requirements)
        self.assertIn(sp.Gt(degeneracy, 0), requirements)
        with self.assertRaises(ValueError):
            state.xreplace({degeneracy: sp.S.Zero})
        with self.assertRaises(ValueError):
            state.xreplace({energy: sp.I})

    def test_positive_integer_degeneracy_is_not_a_normalized_reference(self):
        with self.assertRaises(ValueError):
            CanonicalState((0, 1), sp.S.Zero, (sp.Rational(1, 4), sp.Rational(3, 4)))
        self.assertEqual(query('LogZ', CanonicalState((0, 1), sp.S.Zero, (1, 3))), sp.log(4))

    def test_spectrum_and_degeneracy_must_be_independent_of_beta_parameters(self):
        beta, parameter = sp.symbols('b a')
        for energies, value, degeneracies in (
            ((beta**2, 1), beta, None), ((0, 1), beta, (1, beta)),
            ((parameter, 1), 1/parameter, None)):
            with self.subTest(energies=energies, beta=value), self.assertRaises(ValueError):
                CanonicalState(energies, value, degeneracies)

    def test_input_domains_shapes_and_budgets(self):
        cases = (
            ((), 1), ((0, sp.I), 1), ((0, sp.oo), 1), ((0, 1), sp.I),
            ((0, 1), 1, (1, 0)), ((0, 1), 1, (1, -1)), ((0, 1), 1, (1, 2, 3)),
            ((0, 1), 1, (1, sp.Rational(1, 2))), ((0, 1), 1, (1, 1), 9),
            ((0, 1), 1, (1, 1), 201), (tuple(range(65)), 1),
            ((sp.Symbol('a'), 1), sp.oo), ((sp.Symbol('a'), 1), 1, (1, 1), 50),
        )
        for args in cases:
            with self.subTest(args=args), self.assertRaises((ValueError, TypeError)):
                CanonicalState(*args)

    def test_query_arity_and_assumption_conflicts(self):
        state = CanonicalState((0, 1), sp.Symbol('b'))
        for operation, args in (('Canon', (sp.Tuple(0, 1),)), ('Unknown', (state,)),
                                ('Energy', (state, 1)), ('Energy', (sp.Integer(1),))):
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                canonical_operation(operation, args)
        with self.assertRaises(ValueError):
            canonical_requirements(state, sp.Eq(state.beta, sp.I))

    def test_numeric_queries_keep_tails_and_dist_exactly_normalized(self):
        state = CanonicalState((0, 1), sp.Integer(1000), precision=50)
        probabilities = query('Probabilities', state)
        self.assertTrue(all(isinstance(value, sp.Float) for value in probabilities))
        self.assertTrue(probabilities[1].is_positive)
        distribution = query('Dist', state)
        self.assertEqual(sum(distribution.probabilities), 1)
        self.assertTrue(all(value.is_Rational and value.is_positive for value in distribution.probabilities))
        for operation in ('LogZ', 'Entropy', 'Variance', 'HeatCapacity'):
            with self.subTest(operation=operation):
                self.assertTrue(query(operation, state).is_positive)
        outcome, requirements = canonical_operation('Entropy', (state,))
        self.assertEqual(requirements, ())
        self.assertTrue(outcome.details['numeric_ensemble'])
        self.assertEqual(outcome.details['normalization_residual'], '0')
        self.assertEqual(outcome.details['requested_precision'], 50)
        self.assertGreater(outcome.details['working_precision'], 50)

    def test_numeric_large_energy_origin_does_not_erase_variance(self):
        state = CanonicalState((10**30, 10**30+1), sp.log(3), precision=50)
        variance = query('Variance', state)
        self.assertLess(abs(variance-sp.Rational(3, 16)), sp.Rational(1, 10**45))
        energy = query('Energy', state)
        self.assertLess(abs(energy-(10**30+sp.Rational(1, 4))), sp.Rational(1, 10**18))

    def test_numerical_precision_mode_is_data_and_symbolic_float_is_exactified(self):
        original = CanonicalState((0, 1), sp.Integer(2))
        numeric, requirements = canonical_operation('N', (original, sp.Integer(60)))
        self.assertEqual(numeric.value.precision, 60)
        self.assertEqual(original.precision, 0)
        self.assertEqual(requirements, ())
        beta = sp.Symbol('b')
        symbolic = CanonicalState((sp.Float('0.1'), sp.Float('1.1')), beta)
        outcome, requirements = canonical_operation('Energy', (symbolic,))
        self.assertFalse(outcome.value.has(sp.Float))
        self.assertTrue(outcome.warnings)
        self.assertIn(sp.Contains(beta, sp.S.Reals), requirements)

    def test_coefficient_budget_guards_state_and_derived_observables(self):
        with self.assertRaises(ValueError):
            CanonicalState((0, 2**12000), sp.S.Zero)
        state = CanonicalState((0, 2**7000), sp.S.Zero)
        with self.assertRaises(ValueError):
            query('Variance', state)
        value = CanonicalState((2**11999,), sp.S.Zero)
        self.assertLess(len(str(value)), 4300)


if __name__ == '__main__':
    unittest.main()
