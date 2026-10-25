"""Closed-form finite joint probability and conditional-mass contracts."""

import unittest

import sympy as sp

from mathechan.finite_probability import FiniteDistribution
from mathechan.joint_probability import (
    JointFiniteDistribution, condition_distribution, joint_operation, joint_requirements,
)


def operation(name, *args, assumptions=sp.true):
    return joint_operation(name, args, assumptions)


class JointProbabilityTests(unittest.TestCase):
    def setUp(self):
        self.states = sp.Tuple(sp.Tuple(0,0),sp.Tuple(0,1),sp.Tuple(1,0),sp.Tuple(1,1))
        self.d = JointFiniteDistribution(self.states,
            sp.Tuple(sp.Rational(1,8),sp.Rational(3,8),sp.Rational(1,4),sp.Rational(1,4)))

    def test_joint_distribution_is_immutable_data(self):
        self.assertIsInstance(self.d,sp.Basic)
        self.assertNotIsInstance(self.d,(sp.Expr,sp.Tuple,sp.MatrixBase))
        self.assertEqual(self.d.dimension,2)
        self.assertEqual(joint_requirements(self.d),())
        self.assertEqual(operation("States",self.d)[0].value,self.states)
        self.assertEqual(operation("Probabilities",self.d)[0].value,self.d.probabilities)

    def test_coordinate_marginals_aggregate_exact_masses(self):
        x = operation("MarginalDistribution",self.d,sp.Integer(1))[0].value
        y = operation("MarginalDistribution",self.d,sp.Integer(2))[0].value
        self.assertIsInstance(x,FiniteDistribution)
        self.assertEqual(x.states,sp.Tuple(0,1))
        self.assertEqual(x.probabilities,sp.Tuple(sp.Rational(1,2),sp.Rational(1,2)))
        self.assertEqual(y.probabilities,sp.Tuple(sp.Rational(3,8),sp.Rational(5,8)))
        self.assertEqual(sum(x.probabilities),1)
        self.assertEqual(sum(y.probabilities),1)

    def test_multiple_projection_reorders_coordinates(self):
        marginal = operation("MarginalDistribution",self.d,sp.Tuple(2,1))[0].value
        self.assertIsInstance(marginal,JointFiniteDistribution)
        self.assertEqual(marginal.states,sp.Tuple(*(sp.Tuple(row[1],row[0]) for row in self.states)))
        self.assertEqual(marginal.probabilities,self.d.probabilities)

    def test_singleton_index_list_returns_scalar_distribution(self):
        self.assertEqual(operation("MarginalDistribution",self.d,sp.Tuple(1))[0].value,
                         operation("MarginalDistribution",self.d,sp.Integer(1))[0].value)

    def test_joint_conditional_distribution_and_bayes_identity(self):
        outcome, requirements = condition_distribution(self.d,[False,True,False,True])
        conditioned = outcome.value
        self.assertEqual(requirements,())
        self.assertEqual(conditioned.states,self.states)
        self.assertEqual(conditioned.probabilities,
                         sp.Tuple(0,sp.Rational(3,5),0,sp.Rational(2,5)))
        x = operation("MarginalDistribution",conditioned,1)[0].value
        self.assertEqual(x.probabilities,sp.Tuple(sp.Rational(3,5),sp.Rational(2,5)))
        self.assertEqual(sp.Rational(2,5)*sp.Rational(5,8),sp.Rational(1,4))
        self.assertEqual(outcome.details["conditioning_probability"],"5/8")

    def test_scalar_conditioning_shares_the_same_contract(self):
        d=FiniteDistribution([0,1],[sp.Rational(1,4),sp.Rational(3,4)])
        value,requirements=condition_distribution(d,[False,True])
        self.assertIsInstance(value.value,FiniteDistribution)
        self.assertEqual(value.value.probabilities,sp.Tuple(0,1))
        self.assertEqual(requirements,())

    def test_symbolic_conditioning_keeps_positive_event_before_cancellation(self):
        p=sp.Symbol("p")
        d=JointFiniteDistribution([[0,0],[1,1]],[1-p,p])
        outcome,requirements=condition_distribution(d,[False,True])
        self.assertEqual(outcome.value.probabilities,sp.Tuple(0,1))
        self.assertTrue(any(condition.subs(p,0) is sp.false for condition in requirements))
        self.assertTrue(any("P(A)>0" in warning for warning in outcome.warnings))
        self.assertFalse(any(condition.subs(p,1) is sp.false for condition in requirements))
        self.assertRaises(ValueError,condition_distribution,d.subs(p,0),[False,True])

    def test_zero_probability_event_is_rejected(self):
        self.assertRaises(ValueError,condition_distribution,self.d,[False]*4)
        d=JointFiniteDistribution([[0,0],[1,1]],[1,0])
        self.assertRaises(ValueError,condition_distribution,d,[False,True])

    def test_undecided_event_is_not_silently_selected(self):
        self.assertRaises(ValueError,condition_distribution,self.d,[False,sp.Symbol("a"),False,True])
        self.assertRaises(ValueError,condition_distribution,self.d,[0,1,0,1])
        self.assertRaises(ValueError,condition_distribution,self.d,[True])

    def test_joint_entropy_and_effective_support(self):
        d=JointFiniteDistribution([[0,0],[0,1],[1,0],[1,1]],[sp.Rational(1,4)]*4)
        self.assertEqual(sp.simplify(operation("Entropy",d)[0].value-2*sp.log(2)),0)
        sparse=JointFiniteDistribution([[0,0],[1,1]],[1,0])
        self.assertEqual(operation("Support",sparse)[0].value,sp.Tuple(sp.Tuple(0,0)))
        self.assertEqual(operation("Entropy",sparse)[0].value,0)

    def test_symbolic_row_distinctness_requires_at_least_one_coordinate(self):
        a=sp.Symbol("a")
        d=JointFiniteDistribution([[0,0],[a,0]],[sp.Rational(1,2)]*2)
        self.assertTrue(any(condition.subs(a,0) is sp.false for condition in joint_requirements(d)))
        self.assertRaises(ValueError,d.subs,a,0)
        d=JointFiniteDistribution([[0,0],[a,1]],[sp.Rational(1,2)]*2)
        self.assertFalse(any(condition.subs(a,0) is sp.false for condition in joint_requirements(d)))

    def test_marginal_symbolic_collision_is_explicit_and_recalculable(self):
        a=sp.Symbol("a")
        d=JointFiniteDistribution([[0,0],[a,1]],[sp.Rational(1,2)]*2)
        outcome,requirements=operation("MarginalDistribution",d,1)
        self.assertTrue(any(condition.subs(a,0) is sp.false for condition in requirements))
        specialized=operation("MarginalDistribution",d,1,assumptions=sp.Eq(a,0))[0].value
        self.assertEqual(specialized.states,sp.Tuple(0))
        self.assertEqual(specialized.probabilities,sp.Tuple(1))

    def test_invalid_rows_mass_shapes_and_domain(self):
        cases=(([],[]),([[0,1]],[0]),([[0],[1]],[sp.Rational(1,2)]*2),
               ([[0,1],[0,1]],[sp.Rational(1,2)]*2),([[0,1],[1,2,3]],[sp.Rational(1,2)]*2),
               ([[sp.I,0]],[1]),([[sp.oo,0]],[1]),([[0,1],[1,0]],[-1,2]),
               ([[0,1],[1,0]],[sp.Rational(1,3)]*2))
        for states,masses in cases:
            with self.subTest(states=states),self.assertRaises((ValueError,TypeError)):
                JointFiniteDistribution(states,masses)

    def test_projection_and_moment_errors_are_controlled(self):
        for index in (0,3,sp.Rational(1,2),sp.Tuple(1,1),sp.Tuple()):
            self.assertRaises(ValueError,operation,"MarginalDistribution",self.d,index)
        self.assertRaises(ValueError,operation,"Mean",self.d)
        self.assertRaises(ValueError,operation,"Variance",self.d)

    def test_budgets(self):
        self.assertRaises(ValueError,JointFiniteDistribution,[[i,0] for i in range(65)],
                          [sp.Rational(1,65)]*65)
        self.assertRaises(ValueError,JointFiniteDistribution,[[0]*5],[1])
        symbols=sp.symbols("a:9")
        self.assertRaises(ValueError,JointFiniteDistribution,[[x,0] for x in symbols],
                          [sp.Rational(1,9)]*9)

    def test_binary_float_mass_aggregation_and_conditioning(self):
        d=JointFiniteDistribution([[0,0],[0,1]],[sp.Float("0.25"),sp.Float("0.75")])
        marginal,requirements=operation("MarginalDistribution",d,1)
        self.assertEqual(marginal.value.probabilities,sp.Tuple(1))
        self.assertEqual(requirements,())
        conditional,_=condition_distribution(d,[False,True])
        self.assertEqual(conditional.value.probabilities,sp.Tuple(0,1))
        self.assertTrue(conditional.warnings)


if __name__=="__main__":
    unittest.main()
