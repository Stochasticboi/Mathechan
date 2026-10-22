"""Assumptions are explicit, scoped and preserve conditional provenance."""

import unittest
import sympy as sp
from mathechan import MathechanError, Session, evaluate
from mathechan.kernel import Parser, _evaluate_node
from mathechan.assumptions import combine_assumptions, validate_assumptions


class AssumptionTests(unittest.TestCase):
    def test_sqrt_square_distinguishes_generic_real_and_positive(self):
        self.assertEqual(evaluate('Sqrt[x^2]').text, 'sqrt(x**2)')
        self.assertEqual(evaluate('Assuming[Element[x,Reals],Sqrt[x^2]]').text, 'Abs(x)')
        self.assertEqual(evaluate('Refine[Sqrt[x^2],x>0]').text, 'x')
        self.assertEqual(evaluate('Simplify[Sqrt[x^2],x<0]').text, '-x')
        self.assertEqual(evaluate('Refine[Sqrt[x^2],x>=0]').text, 'x')

    def test_boolean_and_relational_syntax(self):
        for source in ('x>0', 'x>=0', 'x<0', 'x<=0', 'x!=0'):
            self.assertEqual(evaluate(source).kind, 'inequality')
        self.assertEqual(evaluate('And[1<2,Not[False]]').text, 'True')
        self.assertEqual(evaluate('Or[False,2>3]').text, 'False')
        self.assertEqual(evaluate('Element[2,Integers]').text, 'True')
        self.assertEqual(evaluate('Element[Sqrt[-1],Complexes]').text, 'True')
        for source in ('1<x<3', 'x==y==z', 'And[x,True]', 'Not[1]', 'Element[x,3]'):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, evaluate, source)

    def test_nonzero_does_not_silently_make_complex_symbol_real(self):
        self.assertEqual(evaluate('Refine[Sqrt[x^2],x!=0]').text, 'sqrt(x**2)')
        self.assertEqual(evaluate('Refine[Sqrt[x^2],Element[x,Complexes]]').text, 'sqrt(x**2)')
        self.assertEqual(evaluate('Refine[Sqrt[x^2],And[Element[x,Complexes],x!=0]]').text, 'sqrt(x**2)')
        self.assertEqual(evaluate('Assuming[x==Sqrt[-1],x]').text, 'x')

    def test_local_context_does_not_leak_to_next_evaluation(self):
        before = set(sp.assumptions.global_assumptions)
        evaluate('Assuming[x>0,Sqrt[x^2]]')
        self.assertEqual(evaluate('Sqrt[x^2]').text, 'sqrt(x**2)')
        self.assertEqual(set(sp.assumptions.global_assumptions), before)

    def test_contradictions_and_malformed_hypotheses_are_rejected(self):
        for condition in ('And[x>0,x<0]', 'And[x>=2,x<1]', 'And[x==1,x==2]',
                          'And[x>0,Not[x>0]]', 'And[Element[x,Integers],x==1/2]',
                          'And[Element[x,Reals],x==Sqrt[-1]]', 'False', 'x+1'):
            with self.subTest(condition=condition):
                self.assertRaises(MathechanError, evaluate, f'Assuming[{condition},x]')

    def test_ordered_expression_does_not_force_its_symbols_real(self):
        for condition in ('x^2<0', 'And[x^2<0,x==Sqrt[-1]]'):
            with self.subTest(condition=condition):
                result = evaluate(f'Assuming[{condition},x]')
                self.assertEqual(result.text, 'x')
                self.assertEqual(result.status, 'conditional')
        self.assertRaises(MathechanError, evaluate,
                          'Assuming[And[Element[x,Reals],x^2<0],x]')

    def test_joint_linear_and_polynomial_contradictions(self):
        for condition in ('And[x>0,y>0,x+y<0]',
                          'And[x^2+y^2==0,x^2+y^2==1]',
                          'And[Element[x,Reals],x^2+1==0]',
                          'And[Element[x,Integers],x>0,x<1]'):
            with self.subTest(condition=condition):
                self.assertRaises(MathechanError,evaluate,f'Assuming[{condition},x]')
        result=evaluate('Assuming[And[x^2+y^2==0,x==Sqrt[-1],y==1],x]')
        self.assertEqual(result.status,'conditional')
        self.assertEqual(evaluate('Assuming[Sin[x]==0,x]').status,'conditional')

    def test_closed_interval_refines_real_nonnegative_and_detects_conflict(self):
        self.assertEqual(evaluate('Refine[Sqrt[x^2],Element[x,Interval[0,1]]]').text, 'x')
        self.assertRaises(MathechanError, evaluate, 'Assuming[And[Element[x,Interval[0,1]],x<0],x]')
        for source in ('Interval[1,0]', 'Interval[a,b]', 'Interval[0,Infinity]'):
            self.assertRaises(MathechanError, evaluate, source)

    def test_conditions_remain_executable_for_saved_definitions(self):
        capture = {}
        result, value = _evaluate_node(Parser('Assuming[x>0,Sqrt[x^2]]').parse(), '', capture=capture)
        self.assertEqual(value, sp.Symbol('x'))
        self.assertEqual(capture['requirements'], (sp.Symbol('x') > 0,))
        self.assertEqual(result.status, 'conditional')
        self.assertTrue(result.conditions)

    def test_parameter_relations_stay_conditional_without_claim_of_complete_solver(self):
        result = evaluate('Assuming[a>b,Sqrt[(a-b)^2]]')
        self.assertEqual(result.text, 'a - b')
        self.assertEqual(result.status, 'conditional')
        self.assertIn('a > b', result.conditions)
        self.assertIn('undecided', result.details['assumption_validation'])

    def test_persistent_api_refines_without_global_mutation(self):
        x = sp.Symbol('x')
        condition = combine_assumptions(sp.true, x>0)
        result, _ = _evaluate_node(Parser('Sqrt[x^2]').parse(), '', assumptions=condition)
        self.assertEqual(result.text, 'x')
        self.assertEqual(result.status, 'conditional')
        self.assertRaises(ValueError, combine_assumptions, condition, x<0)
        self.assertEqual(validate_assumptions(sp.true), sp.true)

    def test_with_bindings_are_simultaneous_and_protected(self):
        self.assertEqual(evaluate('With[{x,y},{2,3},x+y]').text, '5')
        self.assertEqual(evaluate('With[{x,y},{2,x},y]').text, 'x')
        self.assertEqual(evaluate('x').text, 'x')
        for source in ('With[{Pi},{2},Pi]', 'With[{D},{2},D]', 'With[{x,x},{2,3},x]',
                       'With[{x},{},x]', 'With[{x},{True},x]'):
            self.assertRaises(MathechanError, evaluate, source)

    def test_plot_rejects_false_and_undecidable_hypotheses_at_samples(self):
        self.assertRaises(MathechanError, evaluate,
                          'Plot[Assuming[x>0,Sqrt[x^2]],{x,-1,1}]')
        self.assertRaises(MathechanError, evaluate,
                          'Plot[Assuming[a>0,x],{x,1,2}]')
        session = Session()
        session.evaluate('Assume[x>0]')
        self.assertRaises(MathechanError, session.evaluate, 'Plot[Sqrt[x^2],{x,-1,1}]')
        self.assertEqual(session.evaluate('Plot[Sqrt[x^2],{x,1,2}]').points[0], (1.0, 1.0))

    def test_plot_hypotheses_use_exact_endpoints_and_numeric_parameters(self):
        self.assertRaises(MathechanError, evaluate,
                          'Plot[Assuming[x<Pi,x],{x,1,Pi}]')
        session = Session()
        session.evaluate('k=2')
        session.evaluate('Assume[k>0]')
        self.assertEqual(session.evaluate('Plot[k*x,{x,1,2}]').points[-1], (2.0, 4.0))


if __name__ == '__main__':
    unittest.main()
