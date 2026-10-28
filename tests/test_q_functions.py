"""Exact and numerical identities for real q-deformed functions."""

import unittest

import sympy as sp

from mathechan.q_functions import q_operation
from mathechan.session_storage import Codec


def value(name, x, q):
    return q_operation(name, (x, q))[0].value


class QFunctionTests(unittest.TestCase):
    def test_ordinary_limit_branch(self):
        x=sp.Symbol('x', real=True)
        self.assertEqual(value('QExp', x, 1), sp.exp(x))
        self.assertEqual(value('QLog', sp.Integer(3), 1), sp.log(3))

    def test_exact_values_and_inverse_inside_support(self):
        for q in (sp.Integer(-1), sp.Integer(0), sp.Rational(1,2), sp.Integer(1), sp.Rational(3,2), sp.Integer(2)):
            for x in (sp.Rational(1,2),sp.Integer(1),sp.Integer(2)):
                log=value('QLog',x,q)
                self.assertEqual(sp.simplify(value('QExp',log,q)-x),0)
        self.assertEqual(value('QExp',sp.Integer(2),sp.Rational(1,2)),4)
        self.assertEqual(value('QLog',sp.Integer(4),sp.Rational(1,2)),2)

    def test_cutoff_and_q_above_one_domain(self):
        self.assertEqual(value('QExp',sp.Integer(-2),sp.Rational(1,2)),0)
        self.assertEqual(value('QExp',sp.Integer(-3),sp.Rational(1,2)),0)
        self.assertEqual(value('QExp',sp.Rational(1,2),sp.Integer(2)),2)
        for x in (sp.Integer(1),sp.Integer(2)):
            with self.assertRaises(ValueError):
                value('QExp',x,sp.Integer(2))

    def test_symbolic_q_one_is_selected_without_singular_branch(self):
        x,q=sp.symbols('x q', real=True)
        for name,expected in [('QExp',sp.exp(x)),('QLog',sp.log(x))]:
            expression=value(name,x,q)
            self.assertEqual(expression.subs(q,1),expected)
            self.assertFalse(expression.subs(q,1).has(sp.nan,sp.zoo))
        self.assertEqual(value('QExp',x,q).subs({q:sp.Rational(1,2),x:-3}),0)

    def test_float_unit_order_with_symbolic_argument(self):
        x=sp.Symbol('x',positive=True)
        for name,expected in [('QExp',sp.exp(x)),('QLog',sp.log(x))]:
            outcome,_=q_operation(name,(x,sp.Float(1)))
            self.assertEqual(outcome.value,expected)
            self.assertFalse(outcome.value.has(sp.nan,sp.zoo))
            self.assertTrue(outcome.details['input_approximate'])

    def test_symbolic_requirements_and_cut_derivative_warning(self):
        x,q=sp.symbols('x q')
        outcome, requirements=q_operation('QExp',(x,q))
        self.assertTrue(requirements)
        self.assertTrue(outcome.warnings)
        self.assertTrue(any(condition.has(q) for condition in requirements))
        outcome, requirements=q_operation('QLog',(x,q))
        self.assertIn(sp.Gt(x,0),requirements)

    def test_derivatives_on_open_branch(self):
        x=sp.Symbol('x',positive=True)
        q=sp.Rational(1,2)
        self.assertEqual(sp.simplify(sp.diff(value('QLog',x,q),x)-x**(-q)),0)
        self.assertEqual(sp.simplify(sp.diff(value('QExp',x,q),x)-(1+x/2)),0)

    def test_numeric_near_q_one_and_log_near_one(self):
        q=sp.Float(1+sp.Rational(1,10**50),90)
        x=sp.Float(1+sp.Rational(1,10**40),90)
        actual=value('QLog',x,q)
        # First-order limit: ln(x) differs by O((1-q) ln(x)^2).
        self.assertIsInstance(actual,sp.Float)
        self.assertLess(abs(actual-sp.log(sp.Rational(x)).evalf(90)),sp.Rational(1,10**125))
        actual=value('QExp',sp.Float(1,90),q)
        delta=sp.Rational(q)-1
        reference=sp.E*(1+delta/2+sp.Rational(11,24)*delta**2)
        self.assertLess(abs(actual-reference.evalf(90)),sp.Rational(1,10**85))

    def test_numeric_values_remain_approximate(self):
        for name,x,q in [('QExp',sp.Float(0),sp.Float(1)),('QLog',sp.Float(1),sp.Float(2)),('QExp',sp.Float(-3),sp.Float(.5))]:
            outcome,_=q_operation(name,(x,q))
            self.assertIsInstance(outcome.value,sp.Float)
            self.assertFalse(outcome.details['precision_certified'])

    def test_domain_uses_stored_binary_inputs_before_rounding(self):
        q=sp.Float('1.1')
        x=(1/(q-1)).evalf()
        self.assertEqual(1+(1-q)*x,0)
        # The stored inputs are actually inside the domain, despite a rounded
        # product cancelling to zero at the input precision.
        exact_base=1+(1-sp.Rational(q))*sp.Rational(x)
        self.assertGreater(exact_base,0)
        actual=value('QExp',x,q)
        self.assertTrue(actual.is_finite)
        self.assertGreater(actual,0)

    def test_storage_uses_existing_expression_codec(self):
        x,q=sp.symbols('x q')
        for name in ('QExp','QLog'):
            expression=value(name,x,q)
            restored=Codec().decode(Codec().encode(expression))
            self.assertEqual(restored,expression)
            self.assertEqual(restored.subs(q,1), sp.exp(x) if name=='QExp' else sp.log(x))

    def test_rejects_nonreal_nonfinite_invalid_log_and_giant_exact_power(self):
        for name,x,q in [('QLog',0,1),('QLog',-1,2),('QExp',sp.I,1),('QExp',sp.oo,1),('QExp',1,sp.nan),('QExp',1,1-sp.Rational(1,10**100))]:
            with self.subTest(name=name,x=x,q=q),self.assertRaises(ValueError):
                value(name,x,q)


if __name__=='__main__':
    unittest.main()
