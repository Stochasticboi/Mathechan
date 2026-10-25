"""Reference population identities for moments, transforms and cumulants."""

import unittest

import sympy as sp

from mathechan.finite_probability import FiniteDistribution
from mathechan.joint_probability import JointFiniteDistribution, condition_distribution
from mathechan.parametric_probability import ParametricDistribution
from mathechan.probability_moments import moment_operation


def operation(name, distribution, argument, assumptions=sp.true):
    return moment_operation(name, (distribution, argument), assumptions)[0]


def family(name, *parameters):
    return ParametricDistribution(name+"Distribution", parameters)


class ProbabilityMomentsTests(unittest.TestCase):
    def setUp(self):
        self.coin = FiniteDistribution((-1, 1), (sp.Rational(1, 2), sp.Rational(1, 2)))

    def test_symmetric_coin_population_moments_and_cumulants(self):
        for order in range(13):
            expected = sp.S.Zero if order % 2 else sp.S.One
            self.assertEqual(operation("Moment", self.coin, order).value, expected)
            self.assertEqual(operation("CentralMoment", self.coin, order).value, expected)
        for order, expected in ((1, 0), (2, 1), (3, 0), (4, -2), (5, 0), (6, 16)):
            self.assertEqual(operation("Cumulant", self.coin, order).value, expected)

    def test_scalar_generating_functions_and_positive_cf_sign(self):
        t = sp.Symbol("t", real=True)
        mgf = operation("MGF", self.coin, t).value
        cf = operation("CF", self.coin, t).value
        self.assertEqual(sp.simplify(mgf-sp.cosh(t).rewrite(sp.exp)), 0)
        self.assertEqual(sp.simplify(cf-sp.cos(t).rewrite(sp.exp)), 0)
        constant = FiniteDistribution((3,), (1,))
        characteristic = operation("CF", constant, t).value
        self.assertEqual(sp.diff(characteristic, t).subs(t, 0)/sp.I, 3)
        self.assertEqual(operation("MGF", self.coin, 0).value, 1)
        self.assertEqual(operation("CF", self.coin, 0).value, 1)

    def test_normal_exact_high_order_moments(self):
        normal = family("Normal", 2, 3)
        self.assertEqual(operation("Moment", normal, 2).value, 13)
        self.assertEqual(operation("CentralMoment", normal, 4).value, 243)
        self.assertEqual(operation("CentralMoment", normal, 6).value, 10935)
        self.assertEqual(operation("CentralMoment", normal, 12).value, 5524329195)
        for order in range(1, 13):
            expected = 2 if order == 1 else 9 if order == 2 else 0
            self.assertEqual(operation("Cumulant", normal, order).value, expected)

    def test_poisson_cumulants_and_touchard_moments(self):
        poisson = family("Poisson", 3)
        self.assertEqual(operation("Moment", poisson, 3).value, 57)
        self.assertEqual(operation("Moment", poisson, 4).value, 309)
        for order in range(1, 13):
            self.assertEqual(operation("Cumulant", poisson, order).value, 3)
        zero = family("Poisson", 0)
        self.assertEqual(operation("Moment", zero, 0).value, 1)
        self.assertEqual(operation("Cumulant", zero, 6).value, 0)

    def test_binomial_cumulants_through_six(self):
        binomial = family("Binomial", 3, sp.Rational(1, 3))
        references = (1, sp.Rational(2, 3), sp.Rational(2, 9), -sp.Rational(2, 9),
                      -sp.Rational(10, 27), sp.Rational(14, 81))
        for order, expected in enumerate(references, 1):
            self.assertEqual(operation("Cumulant", binomial, order).value, expected)
        self.assertEqual(operation("Moment", binomial, 3).value, sp.Rational(29, 9))
        for parameters in ((0, sp.Rational(1, 2)), (4, 0), (4, 1)):
            degenerate = family("Binomial", *parameters)
            for order in (2, 4, 6):
                self.assertEqual(operation("CentralMoment", degenerate, order).value, 0)
                self.assertEqual(operation("Cumulant", degenerate, order).value, 0)

    def test_exponential_rate_and_gamma_scale_conventions(self):
        exponential = family("Exponential", 2)
        gamma = family("Gamma", 3, 2)
        self.assertEqual(operation("Moment", exponential, 3).value, sp.Rational(3, 4))
        self.assertEqual(operation("CentralMoment", exponential, 4).value, sp.Rational(9, 16))
        self.assertEqual(operation("Cumulant", exponential, 3).value, sp.Rational(1, 4))
        self.assertEqual(operation("Moment", gamma, 2).value, 48)
        self.assertEqual(operation("CentralMoment", gamma, 2).value, 12)
        self.assertEqual(operation("Cumulant", gamma, 6).value, 23040)

    def test_transform_convergence_and_real_arguments(self):
        t, rate = sp.symbols("t rate")
        distribution = family("Exponential", rate)
        self.assertIn(t < rate, moment_operation("MGF", (distribution, t))[1])
        self.assertTrue(any(condition.has(rate) for condition in moment_operation("Cumulant", (distribution, 3))[1]))
        self.assertFalse(any(condition.has(t) for condition in moment_operation("Cumulant", (distribution, 3))[1]))
        for name in ("MGF", "CF"):
            with self.assertRaises(ValueError):
                operation(name, family("Normal", 0, 1), sp.I)
        with self.assertRaises(ValueError):
            operation("MGF", family("Exponential", 2), 2)
        with self.assertRaises(ValueError):
            operation("MGF", family("Gamma", 3, 2), sp.Rational(1, 2))
        self.assertEqual(operation("CF", family("Exponential", 2), 3).value, sp.Rational(4, 13)+6*sp.I/13)

    def test_joint_correlated_coordinates_and_diagonal_transform(self):
        joint = JointFiniteDistribution(((0, 0), (1, 1)), (sp.Rational(1, 2), sp.Rational(1, 2)))
        self.assertEqual(operation("Moment", joint, (1, 1)).value, sp.Rational(1, 2))
        self.assertEqual(operation("CentralMoment", joint, (1, 1)).value, sp.Rational(1, 4))
        self.assertEqual(operation("Cumulant", joint, (1, 1)).value, sp.Rational(1, 4))
        self.assertEqual(operation("Cumulant", joint, (2, 2)).value, -sp.Rational(1, 8))
        t = sp.Symbol("t", real=True)
        self.assertEqual(operation("MGF", joint, (t, t)).value, (1+sp.exp(2*t))/2)
        self.assertEqual(operation("MGF", joint, (0, 0)).value, 1)
        self.assertEqual(operation("CF", joint, (0, 0)).value, 1)

    def test_independent_joint_mixed_cumulants_vanish(self):
        independent = JointFiniteDistribution(((0, 0), (0, 1), (1, 0), (1, 1)),
                                              (sp.Rational(1, 3), sp.Rational(1, 6),
                                               sp.Rational(1, 3), sp.Rational(1, 6)))
        for orders in ((1, 1), (2, 1), (1, 2), (2, 2), (3, 3)):
            self.assertEqual(operation("Cumulant", independent, orders).value, 0)
        self.assertEqual(operation("CentralMoment", independent, (2, 2)).value, sp.Rational(1, 18))

    def test_four_coordinates_at_total_order_limit(self):
        # Identical coordinates have the scalar Bernoulli cumulant of total
        # order twelve: (2**12-1)*B_12/12 = -691/8.
        identical = JointFiniteDistribution(((0, 0, 0, 0), (1, 1, 1, 1)),
                                            (sp.Rational(1, 2), sp.Rational(1, 2)))
        self.assertEqual(operation("Cumulant", identical, (3, 3, 3, 3)).value, -sp.Rational(691, 8))

    def test_joint_cumulants_agree_with_log_transform_derivative(self):
        s, t = sp.symbols("s t", real=True)
        joint = JointFiniteDistribution(((0, 0), (0, 1), (1, 0), (2, 1)),
                                        (sp.Rational(1, 4),)*4)
        explicit_mgf = (1+sp.exp(t)+sp.exp(s)+sp.exp(2*s+t))/4
        expected = sp.diff(sp.log(explicit_mgf), s, 2, t, 1).subs({s: 0, t: 0})
        self.assertEqual(operation("Cumulant", joint, (2, 1)).value, expected)

    def test_conditioned_moments_compose_with_finite_conditioning(self):
        distribution = FiniteDistribution((0, 1, 2), (sp.Rational(1, 4), sp.Rational(1, 2), sp.Rational(1, 4)))
        conditioned = condition_distribution(distribution, (False, True, True))[0].value
        self.assertEqual(operation("Moment", conditioned, 2).value, 2)
        self.assertEqual(operation("CentralMoment", conditioned, 2).value, sp.Rational(2, 9))
        self.assertEqual(operation("Cumulant", conditioned, 3).value, sp.Rational(2, 27))

    def test_float_centering_does_not_lose_small_variance_to_large_location(self):
        normal = family("Normal", sp.Float("1e100", 50), sp.Rational(1, 3))
        outcome = operation("CentralMoment", normal, 4)
        self.assertTrue(outcome.value.has(sp.Float))
        self.assertLess(abs(outcome.value-sp.Rational(1, 27)), sp.Rational(1, 10**45))
        self.assertTrue(outcome.warnings)
        points = FiniteDistribution((sp.Float("10000000000000000"), sp.Float("10000000000000002")),
                                    (sp.Rational(1, 2), sp.Rational(1, 2)))
        self.assertEqual(operation("CentralMoment", points, 2).value-1, 0)

    def test_symbolic_requirements_survive_zero_order_cancellation(self):
        p = sp.Symbol("p")
        distribution = FiniteDistribution((0, 1), (1-p, p))
        outcome, requirements = moment_operation("Moment", (distribution, 0))
        self.assertEqual(outcome.value, 1)
        self.assertTrue(requirements)
        with self.assertRaises(ValueError):
            moment_operation("Moment", (distribution, 0), p < 0)

    def test_orders_shapes_and_nonfinite_arguments_are_rejected(self):
        joint = JointFiniteDistribution(((0, 0), (1, 1)), (sp.Rational(1, 2), sp.Rational(1, 2)))
        cases = (("Moment", self.coin, -1), ("Moment", self.coin, 13),
                 ("Moment", self.coin, sp.Rational(1, 2)), ("Moment", self.coin, True),
                 ("Moment", self.coin, (1,)), ("Cumulant", self.coin, 0),
                 ("Cumulant", joint, (0, 0)), ("Moment", joint, (12, 1)),
                 ("Moment", joint, 2), ("MGF", joint, (1,)),
                 ("CF", self.coin, sp.oo), ("MGF", self.coin, sp.nan),
                 ("Unknown", self.coin, 2), ("Moment", sp.S.One, 2))
        for name, distribution, argument in cases:
            with self.subTest(name=name, argument=argument), self.assertRaises((ValueError, TypeError)):
                operation(name, distribution, argument)


if __name__ == "__main__":
    unittest.main()
