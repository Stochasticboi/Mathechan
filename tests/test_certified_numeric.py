"""Rational enclosures and error bounds use exact polynomial isolation."""

import json
import unittest
import sympy as sp
from mathechan.certified_numeric import certified_numerical


class CertifiedNumericTests(unittest.TestCase):
    def check_certificate(self,expression,precision=30):
        result=certified_numerical(expression,precision)
        details=result.details
        lower=sp.Rational(details['interval']['lower']); upper=sp.Rational(details['interval']['upper'])
        rounded=sp.Rational(result.value); bound=sp.Rational(details['absolute_error_bound'])
        self.assertLessEqual(lower,upper)
        self.assertGreaterEqual(bound,abs(rounded-lower))
        self.assertGreaterEqual(bound,abs(rounded-upper))
        self.assertTrue(details['certified'])
        self.assertEqual(result.status,'approximate')
        json.dumps(details,allow_nan=False)
        return result,lower,upper

    def test_rationals_include_exact_binary_rounding_error(self):
        for expression in (sp.Rational(1,3),sp.S.Zero,sp.Rational(-2,7),sp.Integer(10)**80):
            with self.subTest(expression=expression):
                result,lower,upper=self.check_certificate(expression)
                self.assertEqual(lower,expression); self.assertEqual(upper,expression)
                self.assertEqual(sp.Rational(result.details['absolute_error_bound']),abs(sp.Rational(result.value)-expression))

    def test_radical_interval_has_exact_polynomial_sign_reference(self):
        result,lower,upper=self.check_certificate(sp.sqrt(2),40)
        self.assertLess(lower**2,2); self.assertGreater(upper**2,2)
        self.assertLess(upper-lower,sp.Rational(1,10)**40)
        self.assertLess(sp.Rational(result.details['relative_error_bound']),sp.Rational(1,10)**39)

    def test_compound_and_trigonometric_real_algebraic_numbers(self):
        for expression in (sp.sqrt(2)+sp.sqrt(3),sp.cos(sp.pi/7),-sp.sqrt(3),sp.real_root(2,3)):
            with self.subTest(expression=expression):
                self.check_certificate(expression,20)

    def test_tiny_real_algebraic_value_has_relative_precision(self):
        result,lower,upper=self.check_certificate(sp.sqrt(2)/10**80,30)
        self.assertGreater(lower,0)
        self.assertLess(upper-lower,sp.Rational(1,10)**100)
        self.assertLess(sp.Rational(result.details['relative_error_bound']),sp.Rational(1,10)**29)

    def test_unsupported_or_uncertain_inputs_are_never_labelled_certified(self):
        x=sp.Symbol('x')
        for expression in (sp.pi,sp.E,sp.Float('1.2'),sp.sqrt(-1),x,sp.oo):
            self.assertRaises(ValueError,certified_numerical,expression)
        for precision in (True,9,201,15.0):
            self.assertRaises(ValueError,certified_numerical,sp.sqrt(2),precision)
        self.assertRaises(ValueError,certified_numerical,sp.Integer(2)**sp.Rational(1,1000))

if __name__=='__main__': unittest.main()
