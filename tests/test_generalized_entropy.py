"""Finite entropy identities, support conventions and numerical limits."""

import unittest

import sympy as sp

from mathechan.finite_probability import FiniteDistribution
from mathechan.joint_probability import JointFiniteDistribution
from mathechan.generalized_entropy import entropy_operation


def finite(masses, states=None):
    return FiniteDistribution(tuple(range(len(masses))) if states is None else states, masses)


def operation(name, *args, assumptions=sp.true):
    return entropy_operation(name, args, assumptions)


class GeneralizedEntropyTests(unittest.TestCase):
    def test_uniform_orders_and_deterministic_limits(self):
        uniform = finite((sp.Rational(1, 4),)*4)
        for order in (0, sp.Rational(1, 2), 1, 2, 3, sp.oo):
            with self.subTest(order=order):
                self.assertEqual(sp.simplify(operation("Renyi", uniform, order)[0].value-sp.log(4)), 0)
        deterministic = finite((0, 1, 0))
        for name in ("Renyi", "Tsallis"):
            for order in (sp.Rational(1, 2), 1, 2):
                self.assertEqual(operation(name, deterministic, order)[0].value, 0)
        self.assertEqual(operation("Renyi", deterministic, 0)[0].value, 0)

    def test_shannon_continuation_and_tsallis_composition(self):
        half = finite((sp.Rational(1, 2),)*2)
        uniform = finite((sp.Rational(1, 4),)*4)
        for name in ("Renyi", "Tsallis"):
            self.assertEqual(sp.simplify(operation(name, half, 1)[0].value-sp.log(2)), 0)
        entropy = operation("Tsallis", half, 2)[0].value
        product = operation("Tsallis", uniform, 2)[0].value
        self.assertEqual(entropy, sp.Rational(1, 2))
        self.assertEqual(product, 2*entropy-entropy**2)

    def test_zero_order_counts_only_positive_support(self):
        distribution = finite((0, sp.Rational(1, 4), sp.Rational(3, 4)))
        self.assertEqual(operation("Renyi", distribution, 0)[0].value, sp.log(2))
        self.assertEqual(operation("Renyi", distribution, sp.oo)[0].value, -sp.log(sp.Rational(3, 4)))

    def test_kl_aligns_labels_and_is_directional(self):
        first = finite((sp.Rational(1, 2),)*2, (3, 7))
        second = finite((sp.Rational(3, 4), sp.Rational(1, 4)), (7, 3))
        value = operation("KL", first, second)[0].value
        self.assertEqual(sp.simplify(value-sp.log(sp.Rational(4, 3))/2), 0)
        self.assertNotEqual(sp.N(value), sp.N(operation("KL", second, first)[0].value))
        self.assertEqual(operation("KL", first, finite((sp.Rational(1, 2),)*2, (7, 3)))[0].value, 0)

    def test_kl_support_mismatch_and_zero_first_mass(self):
        first = finite((0, 1), (0, 1))
        disjoint = finite((1, 0), (0, 1))
        self.assertIs(operation("KL", first, disjoint)[0].value, sp.oo)
        self.assertEqual(operation("KL", first, finite((1,), (1,)))[0].value, 0)
        larger = finite((sp.Rational(1, 4), sp.Rational(3, 4)), (1, 2))
        self.assertEqual(operation("KL", first, larger)[0].value, sp.log(4))

    def test_joint_labels_align_by_rows(self):
        first = JointFiniteDistribution(((0, 0), (1, 1)), (sp.Rational(1, 4), sp.Rational(3, 4)))
        other = JointFiniteDistribution(((1, 1), (0, 0)), (sp.Rational(3, 4), sp.Rational(1, 4)))
        self.assertEqual(operation("KL", first, other)[0].value, 0)
        self.assertEqual(operation("Tsallis", first, 2)[0].value, sp.Rational(3, 8))
        escort = operation("Escort", first, 2)[0].value
        self.assertIsInstance(escort, JointFiniteDistribution)
        self.assertEqual(escort.states, first.states)
        self.assertEqual(escort.probabilities, sp.Tuple(sp.Rational(1, 10), sp.Rational(9, 10)))

    def test_escort_normalizes_and_preserves_zeros(self):
        distribution = finite((0, sp.Rational(1, 3), sp.Rational(2, 3)))
        self.assertEqual(operation("Escort", distribution, 1)[0].value, distribution)
        self.assertEqual(operation("Escort", distribution, 2)[0].value.probabilities,
                         sp.Tuple(0, sp.Rational(1, 5), sp.Rational(4, 5)))

    def test_symbolic_order_continuations_and_requirements(self):
        q = sp.Symbol("q")
        distribution = finite((sp.Rational(1, 2),)*2)
        for name in ("Renyi", "Tsallis"):
            outcome, requirements = operation(name, distribution, q)
            self.assertTrue(requirements)
            self.assertEqual(sp.simplify(outcome.value.subs(q, 1)-sp.log(2)), 0)
        self.assertEqual(operation("Renyi", distribution, q)[0].value.subs(q, 0), sp.log(2))

    def test_symbolic_probabilities_retain_endpoint_branches(self):
        p = sp.Symbol("p")
        distribution = finite((p, 1-p))
        for name in ("Renyi", "Tsallis"):
            value = operation(name, distribution, 1)[0].value
            self.assertEqual(value.subs(p, 0), 0)
            self.assertEqual(value.subs(p, 1), 0)
        support = operation("Renyi", distribution, 0)[0].value
        self.assertEqual(support.subs(p, 0), 0)
        self.assertEqual(support.subs(p, sp.Rational(1, 2)), sp.log(2))

    def test_ambiguous_label_equality_rejected(self):
        a, b = sp.symbols("a b")
        with self.assertRaisesRegex(ValueError, "etiquetas"):
            operation("KL", finite((1,), (a,)), finite((1,), (b,)))
        result = operation("KL", finite((1,), (a,)), finite((1,), (b,)), assumptions=sp.Eq(a, b))[0].value
        self.assertEqual(result, 0)

    def test_domains_and_nonfinite_orders(self):
        distribution = finite((sp.Rational(1, 2),)*2)
        for name, bad in (("Renyi", -1), ("Renyi", sp.I), ("Renyi", -sp.oo),
                          ("Tsallis", 0), ("Tsallis", -1), ("Tsallis", sp.oo),
                          ("Escort", 0), ("Escort", sp.I)):
            with self.subTest(name=name, order=bad), self.assertRaises(ValueError):
                operation(name, distribution, bad)
        with self.assertRaises(ValueError):
            operation("KL", distribution, sp.S.One)

    def test_near_one_uses_guarded_evaluation(self):
        distribution = finite((sp.Rational(1, 4), sp.Rational(3, 4)))
        order = sp.N(1+sp.Rational(1, 10**45), 80)
        shannon = -sp.log(sp.Rational(1, 4))/4-3*sp.log(sp.Rational(3, 4))/4
        for name in ("Renyi", "Tsallis"):
            result = operation(name, distribution, order)[0]
            self.assertEqual(result.status, "approximate")
            self.assertFalse(result.details["precision_certified"])
            self.assertLess(abs(result.value-sp.N(shannon, 80)), sp.Rational(1, 10**43))
            # An independent high precision limit at q=1 agrees to the scale
            # implied by |q-1|, not to all output digits.
            self.assertGreater(result.value, 0)

    def test_approximate_escort_retains_exact_stored_normalization(self):
        distribution = finite((sp.Rational(1, 3), sp.Rational(2, 3)))
        result = operation("Escort", distribution, sp.Float("1.7", 50))[0]
        self.assertEqual(result.status, "approximate")
        self.assertTrue(result.details["input_approximate"])
        self.assertEqual(sum(result.value.probabilities), 1)
        self.assertTrue(all(p > 0 for p in result.value.probabilities))
        self.assertTrue(result.warnings)

    def test_exact_power_budget_is_checked_before_constructing_weights(self):
        distribution = finite((sp.Rational(1, 2),)*2)
        for name in ("Renyi", "Tsallis", "Escort"):
            for order in (sp.Integer(10000), sp.Float(10000)):
                with self.subTest(operation=name, order=order), self.assertRaisesRegex(ValueError, "12000 bits"):
                    operation(name, distribution, order)


if __name__ == "__main__":
    unittest.main()
