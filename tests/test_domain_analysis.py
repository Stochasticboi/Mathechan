"""Reference real domains and conservative principal complex branch reporting."""

import json
import unittest
import sympy as sp
from mathechan.domain_analysis import analyze_domain


class DomainAnalysisTests(unittest.TestCase):
    def setUp(self): self.x=sp.Symbol('x')

    def test_rational_domain_preserves_original_cancelled_exclusion(self):
        r=analyze_domain(sp.S.One,self.x,restrictions=(self.x-1,))
        self.assertEqual(r.value,sp.S.Reals-sp.FiniteSet(1))
        self.assertTrue(r.details['complete'])
        c=analyze_domain(1/(self.x**2+1),self.x,'Complexes')
        self.assertEqual(c.value,sp.S.Complexes-sp.FiniteSet(-sp.I,sp.I))

    def test_log_sqrt_and_inverse_real_domains(self):
        references=[(sp.log(self.x),sp.Interval.open(0,sp.oo)),
                    (sp.sqrt(self.x),sp.Interval(0,sp.oo)),
                    (sp.asin(self.x),sp.Interval(-1,1)),
                    (sp.acos(self.x),sp.Interval(-1,1)),
                    (sp.atan(self.x),sp.S.Reals)]
        for expression, expected in references:
            with self.subTest(expression=expression):
                result=analyze_domain(expression,self.x)
                self.assertEqual(result.value,expected)
                self.assertTrue(result.details['complete'])

    def test_odd_principal_root_does_not_claim_negative_real_output(self):
        result=analyze_domain(self.x**sp.Rational(1,3),self.x)
        self.assertEqual(result.value,sp.Interval(0,sp.oo))

    def test_gamma_poles_have_exact_set(self):
        for domain in ('Reals','Complexes'):
            result=analyze_domain(sp.gamma(self.x),self.x,domain)
            self.assertFalse(result.value.contains(0))
            self.assertFalse(result.value.contains(-2))
            self.assertTrue(result.value.contains(sp.Rational(-1,2)))
            self.assertTrue(result.details['complete'])
        requirement=sp.Not(sp.Contains(self.x,sp.Intersection(sp.S.Integers,sp.Interval(-sp.oo,0))))
        self.assertTrue(analyze_domain(sp.gamma(self.x),self.x,'Complexes',requirements=(requirement,)).details['complete'])

    def test_complex_branch_cuts_do_not_claim_global_holomorphic_domain(self):
        for expression in (sp.log(self.x),sp.sqrt(self.x),sp.asin(self.x),sp.atan(self.x)):
            result=analyze_domain(expression,self.x,'Complexes')
            self.assertFalse(result.details['complete'])
            self.assertEqual(result.status,'unresolved')
            self.assertTrue(result.details['branch_cuts'])
            json.dumps(result.details,allow_nan=False)
        arctangent=analyze_domain(sp.atan(self.x),self.x,'Complexes')
        self.assertFalse(arctangent.value.contains(sp.I))
        self.assertFalse(arctangent.value.contains(-sp.I))

    def test_requirements_and_unknown_parameters_are_not_silently_dropped(self):
        result=analyze_domain(self.x,self.x,requirements=(self.x>0,))
        self.assertEqual(result.value,sp.Interval.open(0,sp.oo))
        a=sp.Symbol('a')
        unknown=analyze_domain(sp.log(self.x-a),self.x)
        self.assertFalse(unknown.details['complete'])
        self.assertEqual(unknown.status,'unresolved')
        complex_order=analyze_domain(self.x,self.x,'Complexes',requirements=(self.x**2<0,))
        self.assertTrue(complex_order.value.has(sp.ConditionSet))

    def test_invalid_input_and_growth_are_rejected(self):
        self.assertRaises(ValueError,analyze_domain,sp.oo,self.x)
        self.assertRaises(ValueError,analyze_domain,self.x,self.x+1)
        self.assertRaises(ValueError,analyze_domain,self.x,self.x,'Integers')

if __name__=='__main__': unittest.main()
