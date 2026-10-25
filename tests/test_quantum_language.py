"""Complex algebra through the public language and persistent sessions."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mathechan import MathechanError, Session, evaluate


class QuantumLanguageTests(unittest.TestCase):
    def test_imaginary_literal_preserves_generic_i(self):
        self.assertEqual(evaluate('Imag^2').text, '-1')
        self.assertEqual(evaluate('Imag-Sqrt[-1]').text, '0')
        self.assertEqual(evaluate('I^2').text, 'I**2')
        for source in ('Imag=2', 'D[x,Imag]', 'Plot[x,{Imag,0,1}]'):
            with self.subTest(source=source), self.assertRaises(MathechanError):
                Session().evaluate(source)

    def test_hermitian_product_differs_from_bilinear_dot(self):
        self.assertEqual(evaluate('Inner[{1,Imag},{1,Imag}]').text, '2')
        self.assertEqual(evaluate('Dot[{1,Imag},{1,Imag}]').text, '0')
        self.assertEqual(evaluate('Inner[{1,0},{Imag,0}]').input, 'Sqrt[-1]')
        self.assertEqual(evaluate('Norm[{3,4}]').text, '5')

    def test_pauli_and_projector_identities(self):
        session = Session()
        session.evaluate('y={{0,-Imag},{Imag,0}}')
        self.assertEqual(session.evaluate('Adj[y]-y').input, 'Matrix[{{0,0},{0,0}}]')
        for source in ('HermQ[y]', 'UnitaryQ[y]', 'HermQ[Proj[{1,Imag}]]',
                       'PSDCheck[Proj[{1,Imag}]]'):
            self.assertEqual(session.evaluate(source).text, 'True')
        self.assertEqual(session.evaluate('Tr[Proj[{1,Imag}]]').text, '1')
        self.assertEqual(session.evaluate('Tr[Dyad[{1,Imag},{1,Imag}]]').text, '2')

    def test_bell_state_and_tensor_order(self):
        session = Session()
        session.evaluate('psi=Unit[{1,0,0,1}]')
        session.evaluate('rho=Proj[psi]')
        for index in (1, 2):
            self.assertEqual(session.evaluate(f'PTrace[rho,{{2,2}},{index}]').input,
                             'Matrix[{{(1/2),0},{0,(1/2)}}]')
        self.assertEqual(session.evaluate('PTrace[rho,{2,2},{1,2}]').text, '1')
        self.assertEqual(evaluate('Kron[{0,1},{1,0}]').input, '{0,0,1,0}')
        self.assertEqual(evaluate('PTrace[Proj[Kron[{0,1},{1,0}]],{2,2},2]').input,
                         'Matrix[{{0,0},{0,1}}]')

    def test_symbolic_queries_specialize_without_activating_equations(self):
        for source, expected in (
            ('HermQ[{{a,0},{0,1}}]/.a->Imag', 'False'),
            ('HermQ[{{a,0},{0,1}}]/.a->2', 'True'),
            ('UnitaryQ[{{a,0},{0,1}}]/.a->1', 'True'),
            ('PSDCheck[{{a,0},{0,1}}]/.a->0', 'True'),
            ('PSDCheck[{{a,0},{0,1}}]/.a->-1', 'False')):
            result = evaluate(source)
            self.assertEqual((result.kind, result.text), ('logical', expected))
        self.assertEqual(evaluate('(x==1)/.x->1').kind, 'equation')
        self.assertEqual(evaluate('{HermQ[{{a}}],x==x}/.{a->Imag,x->2}').input,
                         '{False,(2)==(2)}')

    def test_complex_snapshots_and_logical_queries_roundtrip(self):
        session = Session()
        for source in ('h=HermQ[{{a,0},{0,1}}]', 'p=PSDCheck[{{a,0},{0,1}}]',
                       'c=Conj[z]', 'r=Re[z]', 'm=Im[z]', 'i=Imag', 's=I',
                       'queries={HermQ[{{a,0},{0,1}}],PSDCheck[{{a}}]}'):
            session.evaluate(source)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory)/'session.json'
            session.save(path)
            with patch('mathechan.kernel.build', side_effect=AssertionError('source executed')):
                restored = Session.load(path)
            for source in ('h/.a->Imag', 'p/.a->-1'):
                self.assertEqual(restored.evaluate(source).text, 'False')
            for source in ('c', 'r', 'm', 'i', 's'):
                self.assertEqual(restored.evaluate(source).input, session.evaluate(source).input)
            self.assertEqual(restored.evaluate('queries/.a->Imag').input, '{False,False}')

    def test_norm_conditions_survive_cancellation_and_session_storage(self):
        session = Session()
        session.evaluate('p=Proj[{z}]')
        self.assertEqual(session.evaluate('p').input, 'Matrix[{{1}}]')
        self.assertTrue(session.evaluate('p').conditions)
        with self.assertRaises(MathechanError):
            session.evaluate('p/.z->0')
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory)/'session.json'
            session.save(path)
            restored = Session.load(path)
            with self.assertRaises(MathechanError):
                restored.evaluate('p/.z->0')
            self.assertEqual(restored.evaluate('p/.z->Imag').input, 'Matrix[{{1}}]')

    def test_unsupported_inputs_fail_explicitly(self):
        for source in ('Unit[{0,0}]', 'Proj[{0,0}]', 'Inner[{{1,0}},{1,0}]',
                       'Norm[{{1,0},{0,1}}]', 'Ortho[{{1,0},{2,0}}]',
                       'Kron[IdentityMatrix[8],IdentityMatrix[2]]',
                       'PTrace[IdentityMatrix[4],{2,2},0]', 'Adj=2'):
            with self.subTest(source=source), self.assertRaises(MathechanError):
                Session().evaluate(source)


if __name__ == '__main__':
    unittest.main()
