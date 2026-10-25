"""Named distributions, bound observables and executable domain conditions."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mathechan import MathechanError, Session, evaluate


class ProbabilityExtensionLanguageTests(unittest.TestCase):
    def test_exact_family_references(self):
        for source, expected in (
            ('Mean[BinomialDistribution[10,1/3]]', '10/3'),
            ('Variance[PoissonDistribution[3]]', '3'),
            ('Moment[NormalDistribution[2,3],2]', '13'),
            ('CentralMoment[NormalDistribution[2,3],4]', '243'),
            ('Cumulant[GammaDistribution[2,3],3]', '108'),
            ('PDF[ExponentialDistribution[2],0]', '2'),
            ('CDF[NormalDistribution[0,1],0]', '1/2')):
            with self.subTest(source=source):
                self.assertEqual(evaluate(source).text, expected)

    def test_events_distinguish_continuous_and_discrete_points(self):
        for source, expected in (
            ('Probability[x>0,{x,NormalDistribution[0,1]}]', '1/2'),
            ('Probability[x==0,{x,NormalDistribution[0,1]}]', '0'),
            ('Probability[x==0,{x,PoissonDistribution[0]}]', '1'),
            ('Probability[x>0,{x,PoissonDistribution[0]}]', '0'),
            ('Probability[And[x>=1,x<3],{x,BinomialDistribution[3,1/2]}]', '3/4'),
            ('Probability[Or[x<0,x>0],{x,NormalDistribution[0,1]}]', '1')):
            with self.subTest(source=source):
                self.assertEqual(evaluate(source).text, expected)
        session = Session()
        result = session.evaluate('p=Probability[x+a>0,{x,NormalDistribution[0,1]}]')
        self.assertIn('Contains(a, Reals)', result.conditions)
        self.assertEqual(session.evaluate('p/.a->0').text, '1/2')
        with self.assertRaises(MathechanError):
            session.evaluate('p/.a->Imag')

    def test_observable_binding_and_family_parameter_scope(self):
        session = Session()
        session.evaluate('x=100')
        self.assertEqual(session.evaluate('Expectation[x^2,{x,NormalDistribution[2,3]}]').text, '13')
        self.assertEqual(session.evaluate('x').text, '100')
        self.assertEqual(session.evaluate('Expectation[x,{x,PoissonDistribution[x]}]').text, '100')
        self.assertEqual(evaluate('Covariance[x,x^2,{x,PoissonDistribution[2]}]').text, '10')
        self.assertEqual(evaluate('Correlation[x,2*x,{x,NormalDistribution[0,1]}]').text, '1')

    def test_conditioned_moments_use_positive_event_probability(self):
        self.assertEqual(evaluate('Expectation[x,{x,ExponentialDistribution[2]},x>1]').text, '3/2')
        self.assertEqual(evaluate('Expectation[x^2,{x,NormalDistribution[0,1]},x>0]').text, '1')
        self.assertEqual(evaluate('Expectation[x,{x,BernoulliDistribution[1/2]},x==1]').text, '1')
        with self.assertRaises(MathechanError):
            evaluate('Expectation[x,{x,NormalDistribution[0,1]},x==0]')

    def test_generating_aliases_and_multivariate_cumulants(self):
        for short, long in (('MGF', 'MomentGeneratingFunction'), ('CF', 'CharacteristicFunction')):
            self.assertEqual(evaluate(short+'[NormalDistribution[0,1],t]').text,
                             evaluate(long+'[NormalDistribution[0,1],t]').text)
        d = 'JointFiniteDistribution[{{0,0},{1,1}},{1/2,1/2}]'
        self.assertEqual(evaluate(f'Cumulant[{d},{{1,1}}]').text, '1/4')
        self.assertEqual(evaluate(f'Moment[{d},{{1,1}}]').text, '1/2')
        self.assertEqual(evaluate(f'CF[{d},{{0,0}}]').text, '1')

    def test_saved_distributions_and_transform_domains(self):
        session = Session()
        for source in ('d=GammaDistribution[a,b]', 'g=MGF[ExponentialDistribution[r],t]',
                       'h=Entropy[GammaDistribution[2,3]]', 'f=CDF[NormalDistribution[0,1],z]'):
            session.evaluate(source)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory)/'probability.json'
            session.save(path)
            with patch('mathechan.kernel.build', side_effect=AssertionError('source executed')):
                restored = Session.load(path)
            self.assertEqual(restored.evaluate('h').text, session.evaluate('h').text)
            self.assertEqual(restored.evaluate('CDF[d/.{a->2,b->3},0]').text, '0')
            self.assertEqual(restored.evaluate('g/.{r->2,t->1}').text, '2')
            for source in ('d/.b->0', 'g/.{r->2,t->2}', 'g/.{r->2,t->3}'):
                with self.subTest(source=source), self.assertRaises(MathechanError):
                    restored.evaluate(source)

    def test_parameter_and_order_rejections(self):
        for source in ('BinomialDistribution[-1,1/2]', 'BinomialDistribution[3,2]',
                       'PoissonDistribution[-1]', 'NormalDistribution[0,0]',
                       'GammaDistribution[0,1]', 'ExponentialDistribution[Imag]',
                       'Moment[NormalDistribution[0,1],13]', 'Cumulant[PoissonDistribution[1],0]'):
            with self.subTest(source=source), self.assertRaises(MathechanError):
                evaluate(source)

    def test_float_centering_does_not_erase_small_variance(self):
        import sympy as sp
        for source in (
            'Variance[NormalDistribution[N[10^30,15],1]]',
            'StandardDeviation[NormalDistribution[N[10^30,15],1]]',
            'Covariance[x,x,{x,NormalDistribution[N[10^30,15],1]}]',
            'Correlation[x,x,{x,NormalDistribution[N[10^30,15],1]}]',
            'Expectation[(x-N[10^30,15])^2,{x,NormalDistribution[N[10^30,15],1]}]'):
            with self.subTest(source=source):
                self.assertEqual(sp.simplify(sp.sympify(evaluate(source).text)-1), 0)

    def test_cancelled_holes_require_zero_probability_mass(self):
        for source in (
            'Expectation[Cancel[x/x],{x,PoissonDistribution[0]}]',
            'Expectation[Cancel[(x^2-1)/(x-1)],{x,BinomialDistribution[2,1/2]}]',
            'Probability[Cancel[(x^2-1)/(x-1)]>0,{x,BinomialDistribution[2,1/2]}]'):
            with self.subTest(source=source), self.assertRaises(MathechanError):
                evaluate(source)
        self.assertEqual(evaluate('Expectation[1/(x-1),{x,BinomialDistribution[2,0]}]').text, '-1')
        self.assertEqual(evaluate('Expectation[1/x,{x,BinomialDistribution[2,1]}]').text, '1/2')


if __name__ == '__main__':
    unittest.main()
