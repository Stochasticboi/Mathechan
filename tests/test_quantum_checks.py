"""Exact operator properties and reduced-state reference identities."""

import unittest

import sympy as sp

from mathechan.quantum_checks import check_operation


def operation(name, *args, assumptions=sp.true):
    return check_operation(name, args, assumptions)[0]


class QuantumChecksTests(unittest.TestCase):
    def test_pauli_matrices_are_hermitian_and_unitary(self):
        matrices = (sp.Matrix([[0,1],[1,0]]),sp.Matrix([[0,-sp.I],[sp.I,0]]),sp.diag(1,-1))
        for matrix in matrices:
            with self.subTest(matrix=matrix):
                self.assertIs(operation("HermQ",matrix).value,sp.true)
                self.assertIs(operation("UnitaryQ",matrix).value,sp.true)
                self.assertIs(operation("PSDCheck",matrix).value,sp.false)

    def test_nonhermitian_and_nonunitary_are_false(self):
        self.assertIs(operation("HermQ",sp.Matrix([[0,1],[0,0]])).value,sp.false)
        self.assertIs(operation("UnitaryQ",sp.diag(1,2)).value,sp.false)
        self.assertIs(operation("PSDCheck",sp.diag(sp.I,1)).value,sp.false)

    def test_psd_includes_zero_rank_deficient_and_mixed_states(self):
        for matrix in (sp.zeros(2),sp.diag(1,0),sp.eye(2)/2,sp.Matrix([[1,sp.I],[-sp.I,1]])/2):
            with self.subTest(matrix=matrix):
                self.assertIs(operation("PSDCheck",matrix).value,sp.true)
        self.assertIs(operation("PSDCheck",sp.diag(1,-sp.Rational(1,100))).value,sp.false)

    def test_all_principal_minors_are_checked_not_only_leading(self):
        # Leading minors are 0 and 0, but the second principal minor is -1.
        self.assertIs(operation("PSDCheck",sp.diag(0,-1)).value,sp.false)
        self.assertIs(operation("PSDCheck",sp.diag(0,0,-1)).value,sp.false)

    def test_symbolic_predicates_are_formulas_with_correct_complex_specializations(self):
        a=sp.Symbol("a")
        matrix=sp.diag(a,1)
        herm=operation("HermQ",matrix).value
        positive=operation("PSDCheck",matrix).value
        self.assertNotIn(positive,(sp.true,sp.false))
        for value, expected in ((2,sp.true),(0,sp.true),(-1,sp.false),(sp.I,sp.false)):
            with self.subTest(value=value):
                self.assertIs(sp.simplify(positive.subs(a,value)),expected)
        self.assertIs(sp.simplify(herm.subs(a,sp.I)),sp.false)
        unitary=operation("UnitaryQ",matrix).value
        self.assertIs(sp.simplify(unitary.subs(a,sp.I)),sp.true)
        self.assertIs(sp.simplify(unitary.subs(a,2)),sp.false)

    def test_explicit_assumptions_refine_hermiticity_and_positivity(self):
        a=sp.Symbol("a")
        matrix=sp.diag(a,1)
        self.assertIs(operation("HermQ",matrix,assumptions=sp.Contains(a,sp.S.Reals)).value,sp.true)
        self.assertIs(operation("PSDCheck",matrix,assumptions=sp.Gt(a,0)).value,sp.true)

    def test_float_policy_is_exact_binary_without_hidden_tolerance(self):
        matrix=sp.diag(sp.Float(1),sp.Float(1)+sp.Float("1e-10"))
        outcome=operation("UnitaryQ",matrix)
        self.assertIs(outcome.value,sp.false)
        self.assertTrue(outcome.warnings)
        self.assertEqual(outcome.details["float_policy"],"exact_stored_binary_no_tolerance")
        self.assertIs(operation("PSDCheck",sp.diag(sp.Float(0),sp.Float("-1e-30"))).value,sp.false)

    def test_bell_state_partial_traces_are_maximally_mixed(self):
        rho=sp.ImmutableMatrix([[1,0,0,1],[0,0,0,0],[0,0,0,0],[1,0,0,1]])/2
        for traced in (1,2,sp.Tuple(1),sp.Tuple(2)):
            result=operation("PTrace",rho,sp.Tuple(2,2),traced).value
            self.assertEqual(result,sp.eye(2)/2)
            self.assertEqual(sp.trace(result),sp.trace(rho))

    def test_tensor_order_uses_leftmost_factor_first(self):
        # |0><0| tensor |1><1| has nonzero entry at flat index1.
        rho=sp.diag(0,1,0,0)
        self.assertEqual(operation("PTrace",rho,sp.Tuple(2,2),2).value,sp.diag(1,0))
        self.assertEqual(operation("PTrace",rho,sp.Tuple(2,2),1).value,sp.diag(0,1))

    def test_three_subsystems_and_trace_composition(self):
        rho=sp.diag(0,0,0,0,0,1,0,0)  # |101> in left-to-right order.
        self.assertEqual(operation("PTrace",rho,sp.Tuple(2,2,2),sp.Tuple(1,3)).value,sp.diag(1,0))
        first=operation("PTrace",rho,sp.Tuple(2,2,2),3).value
        second=operation("PTrace",first,sp.Tuple(2,2),1).value
        self.assertEqual(second,sp.diag(1,0))

    def test_trace_all_none_and_dimensions_one(self):
        matrix=sp.ImmutableMatrix([[1,sp.I],[2,3]])
        self.assertEqual(operation("PTrace",matrix,sp.Tuple(2),sp.Tuple()).value,matrix)
        self.assertEqual(operation("PTrace",matrix,sp.Tuple(2),1).value,4)
        self.assertEqual(operation("PTrace",matrix,sp.Tuple(1,2),1).value,matrix)

    def test_partial_trace_is_linear_without_imposing_density_properties(self):
        matrix=sp.ImmutableMatrix(4,4,range(16))
        result=operation("PTrace",matrix,sp.Tuple(2,2),2).value
        self.assertEqual(result,sp.Matrix([[5,9],[21,25]]))
        self.assertEqual(operation("PTrace",2*matrix,sp.Tuple(2,2),2).value,2*result)

    def test_invalid_shapes_dimensions_indices_and_budgets(self):
        cases=(
            ("HermQ",[sp.Matrix([[1,2]])]),("UnitaryQ",[sp.Tuple(1,2)]),
            ("PSDCheck",[sp.eye(5)]),("PTrace",[sp.eye(4),sp.Tuple(2,3),1]),
            ("PTrace",[sp.eye(4),sp.Tuple(2,2),0]),
            ("PTrace",[sp.eye(4),sp.Tuple(2,2),sp.Tuple(1,1)]),
            ("PTrace",[sp.eye(4),sp.Tuple(2,2),3]),
            ("PTrace",[sp.eye(4),sp.Tuple(sp.Rational(1,2),8),1]),
            ("PTrace",[sp.eye(4),sp.Tuple(1,1,1,1,4),1]),
            ("HermQ",[sp.Matrix([[sp.oo]])]),("HermQ",[sp.eye(9)]),
            ("Unknown",[sp.eye(2)]),("PTrace",[sp.eye(2)]),
            ("HermQ",[[["__import__('os')"]]]),
        )
        for name,args in cases:
            with self.subTest(name=name,args=args),self.assertRaises((TypeError,ValueError)):
                operation(name,*args)


if __name__ == "__main__":
    unittest.main()
