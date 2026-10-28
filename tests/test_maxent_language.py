"""Public finite inference, stored witnesses and numerical diagnostics."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sympy as sp

from mathechan import MathechanError, Session, evaluate


def result_node(value):
    if isinstance(value, dict):
        if value.get('type') == 'maxent_result':
            return value
        for item in value.values():
            found = result_node(item)
            if found is not None:
                return found
    if isinstance(value, list):
        for item in value:
            found = result_node(item)
            if found is not None:
                return found
    return None


class MaxEntLanguageTests(unittest.TestCase):
    def test_two_state_exact_inference_and_queries(self):
        session = Session()
        self.assertEqual(session.evaluate('r=MaxEnt[{0,1},1/4]').kind, 'inference')
        for source, expected in (
            ('Probabilities[r]', '{(3/4),(1/4)}'), ('Dual[r]', '{Log[3]}'),
            ('Means[r]', '{(1/4)}'), ('Targets[r]', '{(1/4)}'),
            ('Residuals[r]', '{0}'), ('Active[r]', '{1,2}'),
            ('Rank[r]', '1'), ('Converged[r]', 'True'), ('DualGap[r]', '0')):
            self.assertEqual(session.evaluate(source).text, expected)
        self.assertEqual(session.evaluate('States[Dist[r]]').input, '{1,2}')

    def test_reference_objective_is_distinct_from_shannon(self):
        session = Session()
        session.evaluate('r=MaxEnt[{1,1,1},1,{1/2,1/3,1/6}]')
        self.assertEqual(session.evaluate('Probabilities[r]').input, '{(1/2),(1/3),(1/6)}')
        self.assertEqual(session.evaluate('RelEntropy[r]').text, '0')
        self.assertEqual(session.evaluate('Score[r]').text, '0')
        self.assertEqual(session.evaluate('r').details['objective'], 'relative')
        self.assertEqual(evaluate('Entropy[MaxEnt[{1,1,1},1]]').text, 'log(3)')

    def test_boundary_and_forbidden_reference_states(self):
        session = Session()
        session.evaluate('r=MaxEnt[{0,1,2},0]')
        self.assertEqual(session.evaluate('Probabilities[r]').input, '{1,0,0}')
        self.assertEqual(session.evaluate('Active[r]').input, '{1}')
        self.assertTrue(session.evaluate('r').details['boundary'])
        with self.assertRaises(MathechanError):
            session.evaluate('Dual[r]')
        self.assertEqual(session.evaluate('FaceDual[r]').input, '{0}')
        other = session.evaluate('s=MaxEnt[{0,1,2},1,{1/2,0,1/2}]')
        self.assertFalse(other.details['boundary'])
        self.assertEqual(session.evaluate('Probabilities[s]').input, '{(1/2),0,(1/2)}')

    def test_infeasibility_is_not_only_coordinate_bounds(self):
        for source in (
            'MaxEnt[{{0,0},{1,0},{0,1}},{3/4,3/4}]',
            'MaxEnt[{{0,0},{1,2},{2,4}},{1,3}]',
            'MaxEnt[{0,1,2},2,{1,0,0}]',
            'MaxEnt[{0,1},2]'):
            with self.subTest(source=source), self.assertRaises(MathechanError):
                evaluate(source)

    def test_redundancy_preserves_distribution(self):
        session = Session()
        session.evaluate('r=MaxEnt[{{0,0},{1,2},{2,4}},{1,2}]')
        self.assertEqual(session.evaluate('Rank[r]').text, '1')
        self.assertEqual(session.evaluate('Probabilities[r]').input, '{(1/3),(1/3),(1/3)}')
        self.assertEqual(session.evaluate('Dual[r]').input, '{0,0}')

    def test_numerical_two_observable_reference(self):
        session = Session()
        result = session.evaluate('r=MaxEnt[{{0,0},{1,0},{0,1},{1,1}},{1/3,1/4}]')
        self.assertEqual(result.details['method'], 'damped_newton')
        probabilities = sp.sympify(session.evaluate('Probabilities[r]').text)
        for value, expected in zip(probabilities, (sp.Rational(1,2),sp.Rational(1,4),sp.Rational(1,6),sp.Rational(1,12))):
            self.assertLess(abs(value-expected), sp.Rational(1,10**45))
        self.assertFalse(result.details['precision_certified'])
        self.assertEqual(result.details['normalization_residual'], '0')

    def test_snapshot_load_never_reoptimizes_and_rejects_tampering(self):
        session = Session()
        session.evaluate('r=MaxEnt[{{0,0},{1,0},{0,1},{1,1}},{1/3,1/4}]')
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory)/'maxent.json'
            session.save(path)
            with patch('mathechan.kernel.build', side_effect=AssertionError('source executed')), \
                 patch('mathechan.maxent.solve_maxent', side_effect=AssertionError('optimizer called')), \
                 patch('mathechan.maxent_geometry.prepare_problem', side_effect=AssertionError('LP called')):
                restored = Session.load(path)
            self.assertEqual(restored.evaluate('r').details, session.evaluate('r').details)
            self.assertEqual(restored.evaluate('Residuals[r]').text, session.evaluate('Residuals[r]').text)
            data = json.loads(path.read_text(encoding='utf-8'))
            node = result_node(data)
            self.assertIsNotNone(node)
            node['objective'] = 'unknown'
            path.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaises(MathechanError):
                Session.load(path)

    def test_invalid_input_is_rejected_explicitly(self):
        for source in ('MaxEnt[{0,1},a]', 'MaxEnt[{0,1},Imag]',
                       'MaxEnt[{0,1},1/4,{1,1}]', 'MaxEnt[{0,1},1/4,{-1,2}]',
                       'MaxEnt[{0,1},1/4,{1/2,1/2},9]', 'MaxEnt[{0,1},1/4,{1/2,1/2},101]'):
            with self.subTest(source=source), self.assertRaises(MathechanError):
                evaluate(source)


if __name__ == '__main__':
    unittest.main()
