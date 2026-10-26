"""Finite thermodynamic models through the public language and saved sessions."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mathechan import MathechanError, Session, evaluate


class CanonicalLanguageTests(unittest.TestCase):
    def test_exact_three_level_degenerate_references(self):
        session = Session()
        session.evaluate('r=Canon[{0,1,2},Log[2],{1,2,1}]')
        for source, expected in (
            ('Probabilities[r]', '{(4/9),(4/9),(1/9)}'),
            ('Energy[r]', '2/3'), ('Variance[r]', '4/9'),
            ('Levels[r]', '{0,1,2}'), ('Degens[r]', '{1,2,1}')):
            self.assertEqual(session.evaluate(source).text, expected)
        self.assertEqual(session.evaluate('Simplify[Exp[LogZ[r]]]').text, '9/4')

    def test_entropy_counts_microstates_not_only_levels(self):
        self.assertEqual(evaluate('Entropy[Canon[{0,1,2},0,{1,2,1}]]').input, 'Log[4]')
        self.assertEqual(evaluate('Entropy[Dist[Canon[{0,1,2},0,{1,2,1}]]]').text, '3*log(2)/2')
        self.assertEqual(evaluate('States[Dist[Canon[{2,2},0]]]').input, '{1,2}')
        self.assertEqual(evaluate('Entropy[Canon[{2,2},0]]').text, 'log(2)')

    def test_energy_offset_and_log_partition_derivatives(self):
        for source in (
            'Simplify[Energy[Canon[{3,4},b]]-Energy[Canon[{0,1},b]]-3]',
            'Simplify[FreeEnergy[Canon[{3,4},b]]-FreeEnergy[Canon[{0,1},b]]-3]',
            'Simplify[Variance[Canon[{3,4},b]]-Variance[Canon[{0,1},b]]]',
            'Simplify[D[LogZ[Canon[{0,1},b]],b]+Energy[Canon[{0,1},b]]]',
            'Simplify[(D[LogZ[Canon[{0,1},b]],{b,2}]-Variance[Canon[{0,1},b]])/.b->Log[2]]'):
            with self.subTest(source=source):
                self.assertEqual(evaluate(source).text, '0')

    def test_signed_beta_and_infinite_limits(self):
        self.assertEqual(evaluate('Probabilities[Canon[{0,1},-Log[3]]]').input, '{(1/4),(3/4)}')
        for beta, expected in (('Infinity', '{(1/3),(2/3),0}'), ('-Infinity', '{0,0,1}')):
            self.assertEqual(evaluate(f'Probabilities[Canon[{{0,0,1}},{beta},{{1,2,1}}]]').input, expected)
            self.assertEqual(evaluate(f'HeatCapacity[Canon[{{0,0,1}},{beta},{{1,2,1}}]]').text, '0')
        self.assertEqual(evaluate('FreeEnergy[Canon[{2,3},Infinity]]').text, '2')
        with self.assertRaises(MathechanError):
            evaluate('LogZ[Canon[{2,3},Infinity]]')

    def test_domain_requirements_survive_simplification(self):
        session = Session()
        session.evaluate('s=Entropy[Canon[{a,1},0]]')
        session.evaluate('f=FreeEnergy[Canon[{3},b]]')
        self.assertEqual(session.evaluate('f').text, '3')
        for source in ('s/.a->Imag', 'f/.b->0', 'Canon[{0,1},0,{g,1}]/.g->0',
                       'Canon[{0,1},0,{g,1}]/.g->1/2'):
            with self.subTest(source=source), self.assertRaises(MathechanError):
                session.evaluate(source)

    def test_numeric_model_keeps_precision_and_positive_tail(self):
        result = evaluate('Probabilities[N[Canon[{0,1},1000],30]]')
        self.assertFalse(result.exact)
        self.assertIn('e-435', result.text)
        self.assertFalse(result.details['precision_certified'])
        self.assertEqual(evaluate('Variance[N[Canon[{10^30,10^30+1},0],40]]').text,
                         '0.2500000000000000000000000000000000000000')

    def test_saved_models_load_as_data_without_computing_queries(self):
        session = Session()
        for source in ('r=N[Canon[{0,1,2},Log[2],{1,2,1}],40]',
                       'z=Canon[{2,3},Infinity]', 's=Entropy[Canon[{a,1},0]]',
                       'f=FreeEnergy[Canon[{3},b]]'):
            session.evaluate(source)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory)/'thermal.json'
            session.save(path)
            with patch('mathechan.kernel.build', side_effect=AssertionError('source executed')), \
                 patch('mathechan.canonical_numeric.canonical_numeric_values', side_effect=AssertionError('query computed')):
                restored = Session.load(path)
            self.assertEqual(restored.evaluate('r').input, session.evaluate('r').input)
            self.assertEqual(restored.evaluate('Energy[r]').text, session.evaluate('Energy[r]').text)
            self.assertEqual(restored.evaluate('Energy[z]').text, '2')
            for source in ('s/.a->Imag', 'f/.b->0'):
                with self.assertRaises(MathechanError):
                    restored.evaluate(source)
            data = json.loads(path.read_text(encoding='utf-8'))
            self.assertIn('canonical_state', json.dumps(data))

    def test_fixed_spectrum_and_validated_input_limits(self):
        for source in ('Canon[{0,1},Imag]', 'Canon[{0,1},0,{1,0}]',
                       'Canon[{0,1},0,{1,1/2}]', 'Canon[{b,1},b]',
                       'Canon[{a,1},Infinity]', 'N[Canon[{a,1},b],40]',
                       'N[Canon[{0,1},0],9]', 'FreeEnergy[Canon[{0,1},0]]'):
            with self.subTest(source=source), self.assertRaises(MathechanError):
                evaluate(source)


if __name__ == '__main__':
    unittest.main()
