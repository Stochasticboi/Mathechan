"""Complex-vector identities, tensor ordering and nonzero-norm contracts."""

import unittest
from unittest.mock import patch

import sympy as sp

from mathechan.quantum_algebra import quantum_operation


def operation(name, *arguments, assumptions=sp.true):
    return quantum_operation(name, arguments, assumptions)


def result(name, *arguments, assumptions=sp.true):
    return operation(name, *arguments, assumptions=assumptions)[0].value


class QuantumAlgebraTests(unittest.TestCase):
    def test_scalar_and_elementwise_conjugation_and_components(self):
        self.assertEqual(result("Conj",1+2*sp.I),1-2*sp.I)
        self.assertEqual(result("Conj",sp.Tuple(1+sp.I,2-sp.I)),sp.Tuple(1-sp.I,2+sp.I))
        a = sp.ImmutableMatrix([[1+sp.I,2],[3*sp.I,4-sp.I]])
        self.assertEqual(result("Conj",a),sp.ImmutableMatrix([[1-sp.I,2],[-3*sp.I,4+sp.I]]))
        self.assertEqual(result("Re",a),sp.ImmutableMatrix([[1,2],[0,4]]))
        self.assertEqual(result("Im",a),sp.ImmutableMatrix([[1,0],[3,-1]]))
        self.assertEqual(result("Re",1+2*sp.I),1)
        self.assertEqual(result("Im",sp.Tuple(1+sp.I,2)),sp.Tuple(1,0))

    def test_adjoint_conjugates_and_transposes(self):
        a = sp.ImmutableMatrix([[1+sp.I,2],[3*sp.I,4-sp.I]])
        expected = sp.ImmutableMatrix([[1-sp.I,-3*sp.I],[2,4+sp.I]])
        self.assertEqual(result("Adj",a),expected)
        self.assertEqual(result("Adj",result("Adj",a)),a)
        self.assertEqual(result("Adj",sp.Tuple(1,sp.I)),sp.ImmutableMatrix([[1,-sp.I]]))

    def test_inner_is_hermitian_not_bilinear(self):
        u,v = sp.Tuple(1,sp.I),sp.Tuple(sp.I,2)
        self.assertEqual(result("Inner",u,u),2)
        self.assertEqual(result("Inner",u,v),-sp.I)
        self.assertEqual(result("Inner",v,u),sp.I)
        self.assertEqual(result("Inner",sp.Tuple(sp.I,0),sp.Tuple(1,0)),-sp.I)

    def test_norm_and_unit_for_complex_kets(self):
        v = sp.Tuple(3,4*sp.I)
        self.assertEqual(result("Norm",v),5)
        self.assertEqual(result("Norm",sp.Tuple(0,0)),0)
        expected = sp.Tuple(sp.Rational(3,5),sp.Rational(4,5)*sp.I)
        self.assertEqual(result("Unit",v),expected)
        column = sp.ImmutableMatrix([3,4*sp.I])
        self.assertEqual(result("Unit",column),sp.ImmutableMatrix(expected))
        self.assertEqual(result("Norm",result("Unit",v)),1)

    def test_dyad_orientation(self):
        self.assertEqual(result("Dyad",sp.Tuple(1,0),sp.Tuple(0,1)),
                         sp.ImmutableMatrix([[0,1],[0,0]]))
        self.assertEqual(result("Dyad",sp.Tuple(1,sp.I),sp.Tuple(1,-sp.I)),
                         sp.ImmutableMatrix([[1,sp.I],[sp.I,-1]]))
        self.assertEqual(result("Dyad",sp.Tuple(1,0,0),sp.Tuple(1,0)).shape,(3,2))

    def test_projector_is_normalized_hermitian_idempotent(self):
        p = result("Proj",sp.Tuple(1,sp.I))
        expected = sp.ImmutableMatrix([[sp.Rational(1,2),-sp.I/2],[sp.I/2,sp.Rational(1,2)]])
        self.assertEqual(p,expected)
        self.assertEqual(p*p,p)
        self.assertEqual(p.H,p)
        self.assertEqual(sp.trace(p),1)

    def test_pauli_y_eigenket_and_projector(self):
        y = sp.ImmutableMatrix([[0,-sp.I],[sp.I,0]])
        ket = sp.ImmutableMatrix([1,sp.I])/sp.sqrt(2)
        self.assertEqual(result("Adj",y),y)
        self.assertEqual(y*ket,ket)
        self.assertEqual(result("Inner",ket,y*ket),1)
        self.assertEqual(result("Proj",ket)*ket,ket)

    def test_kron_vector_ordering(self):
        self.assertEqual(result("Kron",sp.Tuple(1,0),sp.Tuple(0,1)),sp.Tuple(0,1,0,0))
        self.assertEqual(result("Kron",sp.Tuple(0,1),sp.Tuple(1,0)),sp.Tuple(0,0,1,0))
        self.assertEqual(result("Kron",sp.Tuple(1,0),sp.Tuple(0,1),sp.Tuple(1,0)),
                         sp.Tuple(0,0,1,0,0,0,0,0))

    def test_kron_matrix_and_mixed_shapes(self):
        x = sp.ImmutableMatrix([[0,1],[1,0]])
        z = sp.ImmutableMatrix([[1,0],[0,-1]])
        expected = sp.ImmutableMatrix([[0,0,1,0],[0,0,0,-1],[1,0,0,0],[0,-1,0,0]])
        self.assertEqual(result("Kron",x,z),expected)
        self.assertEqual(result("Kron",sp.Tuple(1,0),z),
                         sp.ImmutableMatrix([[1,0],[0,-1],[0,0],[0,0]]))

    def test_kron_bounds_checked_before_allocation(self):
        with patch("mathechan.quantum_algebra.sp.kronecker_product",
                   side_effect=AssertionError("oversized allocation")) as allocate:
            with self.assertRaises(ValueError):
                result("Kron",sp.eye(3),sp.eye(3))
            allocate.assert_not_called()

    def test_hermitian_gram_schmidt_known_complex_basis(self):
        basis = result("Ortho",sp.Tuple(sp.Tuple(1,sp.I),sp.Tuple(1,0)))
        expected = sp.Tuple(sp.Tuple(1/sp.sqrt(2),sp.I/sp.sqrt(2)),
                            sp.Tuple(1/sp.sqrt(2),-sp.I/sp.sqrt(2)))
        self.assertEqual(basis,expected)
        for i,left in enumerate(basis):
            for j,right in enumerate(basis):
                self.assertEqual(result("Inner",left,right),int(i==j))

    def test_gram_schmidt_preserves_order_and_rejects_dependence(self):
        basis = result("Ortho",sp.Tuple(sp.Tuple(1,1),sp.Tuple(1,2)))
        self.assertEqual(basis,sp.Tuple(sp.Tuple(1/sp.sqrt(2),1/sp.sqrt(2)),
                                      sp.Tuple(-1/sp.sqrt(2),1/sp.sqrt(2))))
        self.assertRaises(ValueError,result,"Ortho",sp.Tuple(sp.Tuple(1,sp.I),sp.Tuple(2,2*sp.I)))
        self.assertRaises(ValueError,result,"Ortho",sp.Tuple(sp.Tuple(0,0)))

    def test_symbolic_normalization_retains_executable_requirement(self):
        z=sp.Symbol("z")
        for name in ("Unit","Proj"):
            outcome,requirements = operation(name,sp.Tuple(z,0))
            self.assertEqual(outcome.status,"conditional")
            self.assertTrue(requirements)
            self.assertIs(sp.And(*requirements).subs(z,0),sp.false)
            self.assertIs(sp.And(*requirements).subs(z,1+sp.I),sp.true)
        self.assertEqual(result("Proj",sp.Tuple(z)),sp.ImmutableMatrix([[1]]))

    def test_symbolic_norm_never_assumes_reality(self):
        z=sp.Symbol("z")
        self.assertEqual(result("Conj",z),sp.conjugate(z))
        self.assertEqual(result("Norm",sp.Tuple(z)),sp.Abs(z))
        self.assertRaises(ValueError,operation,"Unit",sp.Tuple(z),assumptions=sp.Eq(z,0))
        outcome, requirements=operation("Unit",sp.Tuple(z),assumptions=sp.Gt(z,0))
        self.assertEqual(requirements,())
        self.assertEqual(outcome.value.subs(z,2),sp.Tuple(1))

    def test_float_normalization_and_orthogonality(self):
        a=sp.Float(1,50)
        v=sp.Tuple(a,sp.Float(2,50)*sp.I)
        u=result("Unit",v)
        self.assertLess(abs(result("Inner",u,u)-1),sp.Rational(1,10**45))
        basis=result("Ortho",sp.Tuple(sp.Tuple(a,sp.Float(1,50)),sp.Tuple(a,sp.Float(2,50))))
        for i,left in enumerate(basis):
            for j,right in enumerate(basis):
                self.assertLess(abs(result("Inner",left,right)-int(i==j)),sp.Rational(1,10**45))

    def test_nearly_dependent_float_basis_has_explicit_warning(self):
        a=sp.Float(1,40)
        b=sp.Float("1.00000000000001",40)
        outcome,_=operation("Ortho",sp.Tuple(sp.Tuple(a,a),sp.Tuple(a,b)))
        self.assertTrue(any("casi dependiente" in warning for warning in outcome.warnings))
        self.assertFalse(outcome.details["precision_certified"])
        self.assertTrue(outcome.details["squared_residual_to_input_norm_ratios"])

    def test_zero_vectors_oriented_bras_and_wrong_shapes_rejected(self):
        for name in ("Unit","Proj"):
            self.assertRaises(ValueError,result,name,sp.Tuple(0,0))
        self.assertRaises(ValueError,result,"Inner",sp.Tuple(1,0),sp.Tuple(1))
        self.assertRaises(ValueError,result,"Inner",sp.ImmutableMatrix([[1,2]]),sp.Tuple(1,2))
        self.assertRaises(ValueError,result,"Norm",sp.eye(2))
        self.assertRaises(ValueError,result,"Ortho",sp.Tuple(sp.Tuple(1),sp.Tuple(1)))

    def test_invalid_inputs_and_structural_budgets(self):
        for source in ("arbitrary text",sp.true,sp.oo,sp.nan):
            self.assertRaises(ValueError,result,"Conj",source)
        self.assertRaises(ValueError,result,"Conj",sp.Tuple(*range(9)))
        self.assertRaises(ValueError,result,"Conj",sum(sp.symbols("z0:9")))
        self.assertRaises(ValueError,operation,"Kron",sp.Tuple(1))
        self.assertRaises(ValueError,operation,"Unit",sp.Tuple(1),sp.Tuple(1))
        self.assertRaises(ValueError,operation,"Unknown",sp.Tuple(1))


if __name__ == "__main__":
    unittest.main()
