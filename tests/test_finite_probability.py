"""Analytical finite-space identities and executable probability requirements."""

import unittest

import sympy as sp

from mathechan.finite_probability import (
    FiniteDistribution, distribution_requirements, probability_operation,
)


def operation(name, *args, assumptions=sp.true):
    return probability_operation(name, args, assumptions)


class FiniteProbabilityTests(unittest.TestCase):
    def setUp(self):
        self.d = FiniteDistribution([0,1,2], [sp.Rational(1,4), sp.Rational(1,2), sp.Rational(1,4)])

    def test_distribution_is_basic_not_a_scalar_or_list(self):
        self.assertIsInstance(self.d, sp.Basic)
        self.assertNotIsInstance(self.d, (sp.Expr,sp.Tuple,sp.MatrixBase))
        self.assertEqual(self.d.states, sp.Tuple(0,1,2))
        self.assertEqual(self.d.probabilities, sp.Tuple(sp.Rational(1,4),sp.Rational(1,2),sp.Rational(1,4)))

    def test_moments_of_symmetric_three_state_system(self):
        self.assertEqual(operation("Mean",self.d)[0].value, 1)
        self.assertEqual(operation("Variance",self.d)[0].value, sp.Rational(1,2))
        self.assertEqual(operation("StandardDeviation",self.d)[0].value, sp.sqrt(2)/2)

    def test_zero_mass_entropy_uses_continuous_extension(self):
        d = FiniteDistribution([0,1], [0,1])
        outcome,_ = operation("Entropy",d)
        self.assertEqual(outcome.value,0)
        self.assertEqual(outcome.details["entropy_units"],"nats")
        self.assertFalse(outcome.value.has(sp.nan,sp.zoo))
        self.assertEqual(operation("Support",d)[0].value,sp.Tuple(1))
        self.assertEqual(operation("States",d)[0].value,sp.Tuple(0,1))
        self.assertEqual(operation("Probabilities",d)[0].value,sp.Tuple(0,1))

    def test_fair_binary_entropy_is_log_two(self):
        d = FiniteDistribution([0,1],[sp.Rational(1,2)]*2)
        self.assertEqual(operation("Entropy",d)[0].value,sp.log(2))

    def test_weight_normalization_is_explicit(self):
        with self.assertRaises(ValueError):
            operation("FiniteDistribution",[0,1],[1,3])
        result,conditions=operation("WeightedDistribution",[0,1],[1,3])
        self.assertEqual(result.value.probabilities,sp.Tuple(sp.Rational(1,4),sp.Rational(3,4)))
        self.assertEqual(conditions,())

    def test_symbolic_weights_keep_original_total_even_after_cancellation(self):
        a=sp.Symbol("a")
        result,conditions=operation("WeightedDistribution",[0,1],[a,a])
        self.assertEqual(result.value.probabilities,sp.Tuple(sp.Rational(1,2),sp.Rational(1,2)))
        self.assertTrue(conditions)
        self.assertTrue(any(c.subs(a,0) is sp.false for c in conditions))
        self.assertTrue(any(c.subs(a,-1) is sp.false for c in conditions))

    def test_distinct_symbolic_weights_are_not_false_contradictions(self):
        w=sp.Symbol("w")
        for constant in (1,2):
            result,conditions=operation("WeightedDistribution",[0,1],[w,constant])
            self.assertEqual(sp.simplify(sum(result.value.probabilities)-1),0)
            self.assertTrue(conditions)
            self.assertTrue(any(condition.subs(w,-1) is sp.false for condition in conditions))
            self.assertFalse(any(condition.subs(w,0) is sp.false for condition in conditions))

    def test_symbolic_bernoulli_moments_and_endpoint_entropy(self):
        p=sp.Symbol("p")
        result,conditions=operation("BernoulliDistribution",p)
        self.assertEqual(sp.simplify(operation("Mean",result.value)[0].value-p),0)
        self.assertEqual(sp.simplify(operation("Variance",result.value)[0].value-p*(1-p)),0)
        self.assertTrue(conditions)
        entropy=operation("Entropy",result.value)[0].value
        self.assertEqual(entropy.subs(p,0),0)
        self.assertEqual(entropy.subs(p,1),0)
        self.assertEqual(sp.simplify(entropy.subs(p,sp.Rational(1,2))-sp.log(2)),0)
        self.assertFalse(entropy.has(sp.nan,sp.zoo))

    def test_symbolic_support_requires_deciding_zero_mass(self):
        p=sp.Symbol("p")
        d=operation("BernoulliDistribution",p)[0].value
        with self.assertRaises(ValueError):
            operation("Support",d)
        self.assertEqual(operation("Support",d.subs(p,0))[0].value,sp.Tuple(0))
        self.assertEqual(operation("Support",d,assumptions=sp.And(p>0,p<1))[0].value,sp.Tuple(0,1))
        self.assertEqual(operation("Support",d,assumptions=sp.Eq(p,0))[0].value,sp.Tuple(0))
        self.assertEqual(operation("Support",d,assumptions=sp.Eq(p,1))[0].value,sp.Tuple(1))

    def test_substitution_revalidates_distribution_invariants(self):
        p=sp.Symbol("p")
        d=operation("BernoulliDistribution",p)[0].value
        self.assertRaises(ValueError,d.subs,p,-1)
        self.assertRaises(ValueError,d.subs,p,2)
        self.assertRaises(ValueError,d.subs,p,sp.I)

    def test_incompatible_assumptions_are_rejected(self):
        p=sp.Symbol("p")
        d=operation("BernoulliDistribution",p)[0].value
        self.assertRaises(ValueError,distribution_requirements,d,p<0)
        self.assertRaises(ValueError,operation,"WeightedDistribution",[0,1],[p,p],assumptions=p<0)

    def test_state_collisions_are_requirements(self):
        x=sp.Symbol("x")
        d=FiniteDistribution([0,x],[sp.Rational(1,2)]*2)
        conditions=distribution_requirements(d)
        self.assertTrue(any(c.subs(x,0) is sp.false for c in conditions))
        self.assertRaises(ValueError,d.subs,x,0)

    def test_invalid_data_and_shapes(self):
        cases=([[],[]],[[0],[0]],[[0,1],[sp.Rational(1,2)]],[[0,0],[sp.Rational(1,2)]*2],
               [[0,1],[-1,2]],[[sp.I],[1]],[[0,1],[sp.I,1-sp.I]],[[sp.oo],[1]],
               [[0,1],[sp.Rational(1,3),sp.Rational(1,3)]])
        for args in cases:
            with self.subTest(args=args),self.assertRaises((ValueError,TypeError)):
                FiniteDistribution(*args)
        self.assertRaises(ValueError,operation,"WeightedDistribution",[0,1],[0,0])

    def test_uniform_integer_distribution(self):
        d=operation("DiscreteUniformDistribution",sp.Tuple(1,6))[0].value
        self.assertEqual(operation("Mean",d)[0].value,sp.Rational(7,2))
        self.assertEqual(operation("Variance",d)[0].value,sp.Rational(35,12))
        self.assertEqual(operation("Entropy",d)[0].value,sp.log(6))

    def test_finite_distribution_documented_reference_mean(self):
        d=FiniteDistribution([1,2,3,4],[sp.Rational(1,3),sp.Rational(1,6),sp.Rational(1,4),sp.Rational(1,4)])
        self.assertEqual(operation("Mean",d)[0].value,sp.Rational(29,12))

    def test_binary_float_normalization_has_no_hidden_tolerance(self):
        self.assertRaises(ValueError,FiniteDistribution,[0,1],[sp.Float("0.1"),sp.Float("0.9")])
        d=FiniteDistribution([0,1],[sp.Float("0.25"),sp.Float("0.75")])
        self.assertEqual(distribution_requirements(d),())

    def test_state_and_expression_budgets(self):
        self.assertRaises(ValueError,FiniteDistribution,list(range(65)),[sp.Rational(1,65)]*65)
        self.assertRaises(ValueError,operation,"DiscreteUniformDistribution",sp.Tuple(0,64))
        symbols=sp.symbols("a:9")
        self.assertRaises(ValueError,FiniteDistribution,list(symbols),[sp.Rational(1,9)]*9)
        self.assertRaises(ValueError,FiniteDistribution,[0,1],[sp.Float("1e-10001"),1])


if __name__=="__main__":
    unittest.main()
