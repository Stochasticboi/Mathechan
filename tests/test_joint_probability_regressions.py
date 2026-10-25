"""Joint-event assumptions and numerically centered population moments."""

import unittest
import sympy as sp

from mathechan import evaluate, MathechanError
from mathechan.kernel import Parser, build


class JointProbabilityRegressions(unittest.TestCase):
    distribution = "JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}]"

    def test_equalities_decide_conditioning_events_without_discarding_assumptions(self):
        source = f"Assuming[a==1,ConditionalDistribution[x==a,{{{{x,y}},{self.distribution}}}]]"
        result = evaluate(source)
        self.assertEqual(result.kind,"distribution")
        self.assertTrue(result.conditions)
        self.assertRaises(MathechanError,evaluate,source+"/.a->0")
        value = evaluate(f"Expectation[y,{{{{x,y}},{source}}}]/.a->1")
        self.assertEqual(value.text,"3/4")

    def test_centered_covariance_avoids_large_offset_cancellation(self):
        source = f"Covariance[N[100000000000000000000+x,40],N[100000000000000000000+y,40],{{{{x,y}},{self.distribution}}}]"
        value = build(Parser(source).parse())
        self.assertTrue(abs(value-sp.Rational(1,8)) < sp.Rational(1,10**15))

    def test_zero_covariance_does_not_force_independence(self):
        source = "JointFiniteDistribution[{{-1,1},{0,0},{1,1}},{1/3,1/3,1/3}]"
        self.assertEqual(build(Parser(f"Covariance[x,y,{{{{x,y}},{source}}}]").parse()),0)
        self.assertEqual(evaluate(f"Probability[And[x==0,y==0],{{{{x,y}},{source}}}]").text,"1/3")


if __name__ == "__main__":
    unittest.main()
