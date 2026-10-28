"""Generalized functionals across language, model queries and stored sessions."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mathechan import MathechanError, Session, evaluate


class GeneralizedLanguageTests(unittest.TestCase):
    def test_short_syntax_and_shannon_limit(self):
        for source, expected in (
            ('Renyi[BernoulliDistribution[1/2],2]', 'log(2)'),
            ('Tsallis[BernoulliDistribution[1/2],2]', '1/2'),
            ('Renyi[BernoulliDistribution[1/2],1]', 'log(2)'),
            ('Tsallis[BernoulliDistribution[1/2],1]', 'log(2)'),
            ('QExp[2,1/2]', '4'), ('QLog[4,1/2]', '2')):
            with self.subTest(source=source):
                self.assertEqual(evaluate(source).text, expected)

    def test_escort_composes_with_existing_queries(self):
        session = Session()
        session.evaluate('d=FiniteDistribution[{0,1},{1/4,3/4}]')
        session.evaluate('e=Escort[d,2]')
        self.assertEqual(session.evaluate('Probabilities[e]').text, '{(1/10),(9/10)}')
        self.assertEqual(session.evaluate('Mean[e]').text, '9/10')
        self.assertEqual(session.evaluate('Mean[d]').text, '3/4')

    def test_existing_inference_and_canonical_models_have_explicit_conversion(self):
        self.assertEqual(evaluate('Tsallis[Dist[MaxEnt[{0,1},1/4]],2]').text, '3/8')
        self.assertEqual(evaluate('Renyi[Dist[Canon[{0,1},0]],2]').text, 'log(2)')
        with self.assertRaises(MathechanError):
            evaluate('Tsallis[Canon[{0,1},0],2]')
        for source in ('Dist[MaxEnt[{0,1,2},2/3]]',
                       'Tsallis[Dist[MaxEnt[{0,1,2},2/3]],2]',
                       'Tsallis[Dist[Canon[{0,1},N[1,30]]],2]'):
            self.assertFalse(evaluate(source).exact)

    def test_only_supported_positive_infinity_is_exposed(self):
        source = 'KL[FiniteDistribution[{0},{1}],FiniteDistribution[{1},{1}]]'
        result = evaluate(source)
        self.assertEqual(result.text, 'oo')
        self.assertEqual(result.status, 'divergent')
        self.assertEqual(evaluate('KL[BernoulliDistribution[p],BernoulliDistribution[q]] /. {p->1,q->0}').status,
                         'divergent')
        for invalid in ('1/0', 'Infinity', 'QExp[1,2]', 'QLog[0,2]', 'z='+source):
            with self.subTest(source=invalid), self.assertRaises(MathechanError):
                Session().evaluate(source=invalid)

    def test_symbolic_results_and_maximum_survive_data_only_loading(self):
        session = Session()
        for source in ('r=Renyi[BernoulliDistribution[p],Infinity]',
                       't=Tsallis[BernoulliDistribution[p],q]', 'f=QExp[x,q]'):
            session.evaluate(source)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory)/'generalized.json'
            session.save(path)
            with patch('mathechan.kernel.build', side_effect=AssertionError('source executed')):
                restored = Session.load(path)
            for source, expected in (('r /. p -> 1/2', 'log(2)'),
                                     ('t /. {p -> 1/2,q -> 1}', 'log(2)'),
                                     ('f /. {x -> 2,q -> 1/2}', '4')):
                self.assertEqual(restored.evaluate(source).text, expected)

    def test_approximate_escort_provenance_survives_session(self):
        session = Session()
        result = session.evaluate('e=Escort[BernoulliDistribution[1/4],N[2,30]]')
        self.assertFalse(result.exact)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory)/'approximate.json'
            session.save(path)
            restored = Session.load(path)
            for source in ('e', 'Mean[e]', 'e /. x -> 2', 'Substitute[Mean[e],x,2]'):
                self.assertFalse(restored.evaluate(source).exact)
            data = json.loads(path.read_text(encoding='utf-8'))
            def corrupt(value):
                if isinstance(value, dict):
                    if value.get('kind') == 'stored':
                        value['approximate'] = 'yes'
                    for child in value.values():
                        corrupt(child)
                elif isinstance(value, list):
                    for child in value:
                        corrupt(child)
            corrupt(data)
            path.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaises(MathechanError):
                Session.load(path)

    def test_substitution_cannot_construct_an_unbounded_rational_power(self):
        session = Session()
        session.evaluate('t=Tsallis[BernoulliDistribution[1/2],q]')
        with self.assertRaises(MathechanError):
            session.evaluate('t /. q -> 10^100')
        with self.assertRaises(MathechanError):
            session.evaluate('Substitute[t,q,10^100]')
        self.assertEqual(session.evaluate('t /. q -> 2').text, '1/2')

    def test_public_names_are_protected(self):
        for name in ('Renyi', 'Tsallis', 'KL', 'Escort', 'QExp', 'QLog'):
            with self.subTest(name=name), self.assertRaises(MathechanError):
                Session().evaluate(name+'=1')

    def test_low_precision_input_is_not_reported_as_fifteen_digits(self):
        result = evaluate('Tsallis[BernoulliDistribution[1/2],N[Pi,1]]')
        self.assertFalse(result.exact)
        self.assertEqual(result.details['requested_significant_digits'], 1)

    def test_user_functions_preserve_power_budgets_and_regular_branches(self):
        session = Session()
        session.evaluate('Define[f,{q},Tsallis[BernoulliDistribution[1/2],q]]')
        with self.assertRaises(MathechanError):
            session.evaluate('f[10000]')
        self.assertEqual(session.evaluate('f[2]').text, '1/2')
        session.evaluate('Define[g,{q},QExp[2,q]]')
        self.assertEqual(session.evaluate('g[1]').text, 'exp(2)')
        self.assertEqual(session.evaluate('g[1/2]').text, '4')


if __name__ == '__main__':
    unittest.main()
