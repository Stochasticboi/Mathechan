"""Independent normalization, boundary and transform checks for scalar families."""

import unittest

import sympy as sp

from mathechan.parametric_probability import (
    ParametricDistribution, parametric_requirements, parametric_operation,
    parametric_raw_moment, parametric_transform, parametric_density,
    parametric_cdf, parametric_support,
)


def distribution(family, *parameters):
    return ParametricDistribution(family+"Distribution", parameters)


def query(name, *args, assumptions=sp.true):
    return parametric_operation(name, args, assumptions)[0]


class ParametricProbabilityTests(unittest.TestCase):
    def test_representation_is_immutable_data_and_revalidates_substitution(self):
        p = sp.Symbol("p")
        d = distribution("Binomial", 3, p)
        self.assertIsInstance(d, sp.Basic)
        self.assertNotIsInstance(d, sp.Expr)
        self.assertTrue(d.is_discrete)
        self.assertEqual(d.parameters, sp.Tuple(3, p))
        self.assertEqual(d.subs(p, sp.Rational(1, 2)).family, "BinomialDistribution")
        with self.assertRaises(ValueError):
            d.subs(p, 2)

    def test_invalid_parameters_and_nonfinite_inputs_are_rejected(self):
        cases = (("Binomial", (-1, sp.Rational(1, 2))), ("Binomial", (sp.Rational(1, 2), 1)),
                 ("Binomial", (2, -1)), ("Poisson", (-1,)), ("Normal", (0, 0)),
                 ("Normal", (sp.I, 1)), ("Exponential", (0,)), ("Gamma", (1, -1)),
                 ("Gamma", (sp.oo, 1)), ("Normal", (sp.nan, 1)))
        for family, parameters in cases:
            with self.subTest(family=family, parameters=parameters), self.assertRaises(ValueError):
                distribution(family, *parameters)

    def test_symbolic_domains_remain_executable_requirements(self):
        n, p, rate = sp.symbols("n p rate")
        d = distribution("Binomial", n, p)
        requirements = parametric_requirements(d)
        self.assertIn(sp.Contains(n, sp.S.Integers), requirements)
        self.assertIn(sp.Ge(n, 0), requirements)
        self.assertIn(sp.Ge(p, 0), requirements)
        self.assertIn(sp.Le(p, 1), requirements)
        d = distribution("Exponential", rate)
        self.assertIn(sp.Gt(rate, 0), parametric_requirements(d))
        with self.assertRaises(ValueError):
            parametric_requirements(d, rate < 0)

    def test_binomial_masses_normalization_and_noninteger_mass(self):
        d = distribution("Binomial", 5, sp.Rational(1, 3))
        masses = [parametric_density(d, sp.Integer(k)) for k in range(6)]
        self.assertEqual(sum(masses), 1)
        self.assertEqual(sum(k*p for k, p in enumerate(masses)), sp.Rational(5, 3))
        self.assertEqual(sum(k**2*p for k, p in enumerate(masses)), sp.Rational(35, 9))
        for x in (-1, 6, sp.Rational(1, 2)):
            self.assertEqual(parametric_density(d, sp.sympify(x)), 0)

    def test_poisson_probability_mass_normalizes_on_integer_support(self):
        d = distribution("Poisson", 2)
        k = sp.Symbol("k", integer=True, nonnegative=True)
        self.assertEqual(sp.summation(parametric_density(d, k), (k, 0, sp.oo)), 1)
        self.assertEqual(parametric_cdf(d, sp.Integer(0)), sp.exp(-2))
        self.assertEqual(parametric_cdf(d, sp.Rational(3, 2)), 3*sp.exp(-2))
        self.assertEqual(parametric_density(d, sp.Rational(1, 2)), 0)

    def test_degenerate_discrete_families_have_exact_mass_and_support(self):
        for d, point in ((distribution("Poisson", 0), 0),
                         (distribution("Binomial", 4, 0), 0),
                         (distribution("Binomial", 4, 1), 4),
                         (distribution("Binomial", 0, sp.Rational(1, 3)), 0)):
            with self.subTest(distribution=d):
                self.assertEqual(parametric_support(d), sp.FiniteSet(point))
                self.assertEqual(parametric_density(d, sp.Integer(point)), 1)
                self.assertEqual(parametric_density(d, sp.Integer(point+1)), 0)
                self.assertEqual(parametric_cdf(d, sp.Integer(point-1)), 0)
                self.assertEqual(parametric_cdf(d, sp.Integer(point)), 1)
                self.assertEqual(query("Variance", d).value, 0)
                self.assertEqual(query("Entropy", d).value, 0)

    def test_continuous_densities_integrate_to_one(self):
        x = sp.Symbol("x", real=True)
        normal = distribution("Normal", 1, 2)
        self.assertEqual(sp.integrate(parametric_density(normal, x), (x, -sp.oo, sp.oo)), 1)
        for d in (distribution("Exponential", 2), distribution("Gamma", 2, 3)):
            self.assertEqual(sp.integrate(parametric_density(d, x), (x, 0, sp.oo)), 1)
            self.assertEqual(parametric_density(d, sp.Integer(-1)), 0)

    def test_cdf_boundaries_and_normal_symmetry(self):
        for d in (distribution("Normal", 3, 2), distribution("Exponential", 2),
                  distribution("Gamma", 2, 3), distribution("Poisson", 2),
                  distribution("Binomial", 4, sp.Rational(1, 2))):
            self.assertEqual(parametric_cdf(d, -sp.oo), 0)
            self.assertEqual(parametric_cdf(d, sp.oo), 1)
        self.assertEqual(parametric_cdf(distribution("Normal", 3, 2), sp.Integer(3)), sp.Rational(1, 2))
        self.assertEqual(parametric_cdf(distribution("Gamma", 2, 3), sp.Integer(0)), 0)
        self.assertEqual(parametric_cdf(distribution("Binomial", 4, sp.Rational(1, 2)), sp.Integer(2)), sp.Rational(11, 16))

    def test_gamma_scale_convention_agrees_with_exponential(self):
        x = sp.Symbol("x", positive=True)
        gamma = distribution("Gamma", 1, sp.Rational(1, 2))
        exponential = distribution("Exponential", 2)
        self.assertEqual(sp.simplify(parametric_density(gamma, x)-parametric_density(exponential, x)), 0)
        for order in range(13):
            self.assertEqual(parametric_raw_moment(gamma, order), parametric_raw_moment(exponential, order))
        self.assertEqual(sp.simplify(query("Entropy", gamma).value-query("Entropy", exponential).value), 0)

    def test_moments_match_low_order_reference_values(self):
        values = ((distribution("Binomial", 5, sp.Rational(1, 3)), sp.Rational(5, 3), sp.Rational(10, 9)),
                  (distribution("Poisson", 3), 3, 3), (distribution("Normal", 2, 3), 2, 9),
                  (distribution("Exponential", 2), sp.Rational(1, 2), sp.Rational(1, 4)),
                  (distribution("Gamma", 2, 3), 6, 18))
        for d, mean, variance in values:
            self.assertEqual(query("Mean", d).value, mean)
            self.assertEqual(query("Variance", d).value, variance)
            self.assertEqual(parametric_raw_moment(d, 0), 1)
        self.assertEqual(parametric_raw_moment(distribution("Normal", 0, 1), 4), 3)
        self.assertEqual(parametric_raw_moment(distribution("Poisson", 2), 3), 22)

    def test_transform_normalization_and_first_derivatives(self):
        t = sp.Symbol("t", real=True)
        families = (distribution("Binomial", 5, sp.Rational(1, 3)), distribution("Poisson", 2),
                    distribution("Normal", 2, 3), distribution("Exponential", 2), distribution("Gamma", 2, 3))
        for d in families:
            mgf, _ = parametric_transform(d, t)
            cf, conditions = parametric_transform(d, t, characteristic=True)
            self.assertEqual(mgf.subs(t, 0), 1)
            self.assertEqual(cf.subs(t, 0), 1)
            self.assertEqual(sp.diff(mgf, t).subs(t, 0), query("Mean", d).value)
            self.assertEqual(sp.simplify(sp.diff(cf, t).subs(t, 0)/sp.I), query("Mean", d).value)
            self.assertEqual(conditions, ())

    def test_transform_convergence_is_retained_and_boundary_rejected(self):
        t = sp.Symbol("t")
        for d, boundary in ((distribution("Exponential", 2), 2), (distribution("Gamma", 3, 2), sp.Rational(1, 2))):
            _, conditions = parametric_transform(d, t)
            self.assertIn(sp.Contains(t, sp.S.Reals), conditions)
            self.assertIn(t < boundary, conditions)
            with self.assertRaises(ValueError):
                parametric_transform(d, boundary)
            _, conditions = parametric_transform(d, boundary, characteristic=True)
            self.assertEqual(conditions, ())

    def test_entropy_measure_and_pending_sum_are_explicit(self):
        d = distribution("Binomial", 1, sp.Rational(1, 2))
        self.assertEqual(query("Entropy", d).value, sp.log(2))
        self.assertEqual(query("Entropy", d).details["entropy_kind"], "Shannon")
        for d in (distribution("Normal", 0, 1), distribution("Exponential", 2), distribution("Gamma", 2, 3)):
            self.assertEqual(query("Entropy", d).details["entropy_kind"], "differential")
        outcome = query("Entropy", distribution("Poisson", 2))
        self.assertTrue(outcome.value.has(sp.Sum))
        self.assertEqual(outcome.status, "unresolved")
        self.assertTrue(outcome.warnings)

    def test_pdf_gamma_boundary_can_diverge_without_invalid_distribution(self):
        d = distribution("Gamma", sp.Rational(1, 2), 1)
        outcome = query("PDF", d, sp.S.Zero)
        self.assertEqual(outcome.value, sp.oo)
        self.assertEqual(outcome.status, "divergent")
        self.assertEqual(query("CDF", d, sp.S.Zero).value, 0)

    def test_gamma_boundary_agrees_with_specializing_the_density(self):
        x = sp.Symbol("x", real=True)
        for shape in (sp.Rational(1, 2), sp.S.One, sp.Integer(2)):
            d = distribution("Gamma", shape, 3)
            self.assertEqual(parametric_density(d, x).subs(x, 0), parametric_density(d, sp.S.Zero))
        shape = sp.Symbol("shape", positive=True)
        d = distribution("Gamma", shape, 3)
        density = parametric_density(d, x)
        self.assertEqual(density.subs({shape: 1, x: 0}), sp.Rational(1, 3))


if __name__ == "__main__":
    unittest.main()
