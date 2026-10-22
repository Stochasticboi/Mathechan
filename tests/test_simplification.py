"""Exact identities and branch-sensitive bounded simplification."""

import unittest
from unittest.mock import patch
import sympy as sp
from mathechan.simplification import full_simplify_expression


class FullSimplifyTests(unittest.TestCase):
    def test_rational_and_trigonometric_identities(self):
        x=sp.Symbol('x')
        for expression, expected in [((x**2-1)/(x-1),x+1),
                                     (sp.sin(x)**2+sp.cos(x)**2,sp.S.One)]:
            outcome=full_simplify_expression(expression)
            self.assertEqual(sp.simplify(outcome.value-expected),0)
            self.assertLessEqual(outcome.details['output_operations'],outcome.details['input_operations'])

    def test_principal_branches_require_explicit_hypotheses(self):
        x=sp.Symbol('x')
        generic=full_simplify_expression(sp.sqrt(x**2))
        self.assertEqual(generic.value,sp.sqrt(x**2))
        positive=full_simplify_expression(sp.sqrt(x**2), assumptions=x>0)
        self.assertEqual(positive.value,x)
        self.assertEqual(positive.status,'conditional')
        self.assertIn('x > 0',positive.conditions)
        self.assertEqual(full_simplify_expression(sp.sqrt(x**2),assumptions=sp.Contains(x,sp.S.Reals)).value,sp.Abs(x))

    def test_original_exclusions_and_requirements_remain_explicit(self):
        x=sp.Symbol('x')
        result=full_simplify_expression(sp.S.One,restrictions=(x,),requirements=(x>0,))
        self.assertEqual(result.value,1)
        self.assertTrue(any('!= 0' in condition for condition in result.conditions))
        self.assertEqual(result.status,'conditional')

    def test_no_unverified_transform_is_selected(self):
        x=sp.Symbol('x')
        with patch('mathechan.simplification.sp.trigsimp',return_value=x+999):
            self.assertEqual(full_simplify_expression(x).value,x)

    def test_growth_is_rejected_before_transformations(self):
        x,y,z=sp.symbols('x y z')
        expression=(x+y+z)**100
        with patch('mathechan.simplification.sp.simplify',side_effect=AssertionError('expansion')):
            self.assertRaises(ValueError,full_simplify_expression,expression)
        self.assertRaises(ValueError,full_simplify_expression,sp.Matrix([[1]]))
        self.assertRaises(ValueError,full_simplify_expression,sp.oo)

if __name__=='__main__': unittest.main()
