"""Independent identities for bounded spectral calculations."""

import unittest

import sympy as sp

from mathechan.matrix_spectral import spectral_operation


class MatrixSpectralTests(unittest.TestCase):
    def operation(self, name, matrix, assumptions=sp.true):
        return spectral_operation(name, [sp.ImmutableMatrix(matrix)], assumptions)

    def assertMatrixEqual(self, actual, expected):
        self.assertTrue((sp.Matrix(actual) - sp.Matrix(expected)).applyfunc(sp.simplify).is_zero_matrix)

    def test_eigenvalues_multiplicity_and_characteristic_polynomial(self):
        matrix = sp.Matrix([[2, 1, 0], [0, 2, 1], [0, 0, -3]])
        outcome, requirements = self.operation("Eigenvalues", matrix)
        self.assertEqual(outcome.value, sp.Tuple(-3, 2, 2))
        self.assertEqual(requirements, ())
        self.assertEqual(sum(outcome.value), matrix.trace())
        self.assertEqual(sp.prod(outcome.value), matrix.det())

    def test_repeated_diagonal_eigenspace_is_complete(self):
        outcome, _ = self.operation("Eigenvectors", sp.diag(2, 2, -1))
        self.assertTrue(outcome.details["basis_complete"])
        self.assertEqual(sorted(outcome.details["geometric_multiplicities"]), [1, 2])
        self.assertEqual(sp.Matrix.hstack(*(sp.Matrix(v) for v in outcome.value)).rank(), 3)

    def test_defective_jordan_returns_no_zero_padding(self):
        outcome, _ = self.operation("Eigenvectors", [[2, 1], [0, 2]])
        self.assertEqual(outcome.status, "evaluated")
        self.assertEqual(outcome.value, sp.Tuple(sp.Tuple(1, 0)))
        self.assertFalse(outcome.details["basis_complete"])
        self.assertEqual(outcome.details["algebraic_multiplicities"], [2])
        self.assertTrue(outcome.warnings)

    def test_complex_right_eigenvectors(self):
        matrix = sp.Matrix([[0, -1], [1, 0]])
        outcome, _ = self.operation("Eigenvectors", matrix)
        eigenvalues = list(map(sp.sympify, outcome.details["eigenvalues_for_vectors"]))
        self.assertEqual(set(eigenvalues), {-sp.I, sp.I})
        for eigenvalue, vector in zip(eigenvalues, outcome.value):
            self.assertMatrixEqual(matrix * sp.Matrix(vector), eigenvalue * sp.Matrix(vector))

    def test_float_defective_matrix_remains_defective(self):
        outcome, _ = self.operation("Eigenvectors", [[1.0, 1.0], [0.0, 1.0]])
        self.assertFalse(outcome.details["basis_complete"])
        self.assertEqual(len(outcome.value), 1)
        self.assertFalse(outcome.details["precision_certified"])
        self.assertTrue(outcome.value.atoms(sp.Float))

    def test_float_vectors_relative_and_absolute_residual(self):
        matrix = sp.Matrix([[1.25, -2.5], [2.5, 1.25]])
        outcome, _ = self.operation("Eigenvectors", matrix)
        eigenvalues = list(map(sp.sympify, outcome.details["eigenvalues_for_vectors"]))
        # atol=rtol=1e-12, infinity norm, stored input (not an uncertainty bound).
        for eigenvalue, vector in zip(eigenvalues, outcome.value):
            vector = sp.Matrix(vector)
            residual = max(float(abs(sp.N(x))) for x in matrix * vector - eigenvalue * vector)
            scale = float(matrix.norm(sp.oo) * vector.norm(sp.oo) + abs(eigenvalue) * vector.norm(sp.oo))
            self.assertLessEqual(residual, 1e-12 + 1e-12 * scale)

    def test_symbolic_defective_rank_condition_survives_cancellation(self):
        a = sp.Symbol("a")
        outcome, requirements = self.operation("Eigenvectors", [[0, a], [0, 0]])
        self.assertEqual(outcome.status, "conditional")
        self.assertIn(sp.Ne(a, 0), requirements)
        self.assertTrue(any(condition.subs(a, 0) is sp.false for condition in requirements))

    def test_parameter_degeneracy_has_executable_denominator_condition(self):
        a, b = sp.symbols("a b")
        outcome, requirements = self.operation("Eigenvectors", [[a, 1], [0, b]])
        self.assertEqual(len(outcome.value), 2)
        self.assertTrue(any(condition.subs(b, a) is sp.false for condition in requirements))
        self.assertTrue(outcome.details["basis_complete"])

    def test_diagonal_parameter_coincidence_keeps_universal_basis(self):
        a, b = sp.symbols("a b")
        outcome, requirements = self.operation("Eigenvectors", sp.diag(a, b))
        self.assertEqual(requirements, ())
        self.assertEqual(outcome.status, "evaluated")
        self.assertTrue(outcome.details["basis_complete"])
        self.assertIsNone(outcome.details["algebraic_multiplicities"])
        self.assertTrue(outcome.details["multiplicities_require_specialization"])
        columns = sp.Matrix.hstack(*(sp.Matrix(vector) for vector in outcome.value))
        self.assertEqual(columns.subs(b, a).rank(), 2)
        for eigenvalue, vector in zip(outcome.details["eigenvalues_for_vectors"], outcome.value):
            self.assertMatrixEqual(sp.diag(a, b) * sp.Matrix(vector), sp.sympify(eigenvalue) * sp.Matrix(vector))

    def test_input_pole_conditions(self):
        a = sp.Symbol("a")
        _, requirements = self.operation("Eigenvalues", [[1/a, 0], [0, 2]])
        self.assertIn(sp.Ne(a, 0), requirements)

    def test_assumptions_discharge_conditions(self):
        a = sp.Symbol("a")
        outcome, requirements = self.operation("Eigenvectors", [[0, a], [0, 0]], sp.Q.positive(a))
        self.assertEqual(requirements, ())
        self.assertEqual(outcome.status, "evaluated")

    def test_exponential_nilpotent_series_terminates(self):
        matrix = sp.Matrix([[0, 1, 0], [0, 0, 2], [0, 0, 0]])
        outcome, _ = self.operation("MatrixExp", matrix)
        self.assertMatrixEqual(outcome.value, sp.eye(3) + matrix + matrix**2/2)

    def test_exponential_jordan(self):
        outcome, _ = self.operation("MatrixExp", [[2, 1], [0, 2]])
        self.assertMatrixEqual(outcome.value, sp.exp(2) * sp.Matrix([[1, 1], [0, 1]]))

    def test_exponential_symbolic_rotation(self):
        t = sp.Symbol("t", real=True)
        outcome, requirements = self.operation("MatrixExp", [[0, -t], [t, 0]])
        self.assertMatrixEqual(outcome.value, [[sp.cos(t), -sp.sin(t)], [sp.sin(t), sp.cos(t)]])
        self.assertEqual(requirements, ())

    def test_exponential_symbolic_divided_difference(self):
        a, b = sp.symbols("a b")
        outcome, requirements = self.operation("MatrixExp", [[a, 1], [0, b]])
        self.assertTrue(any(condition.subs(b, a) is sp.false for condition in requirements))
        at_point = outcome.value.subs({a: 0, b: 1})
        self.assertMatrixEqual(at_point, [[1, sp.E-1], [0, sp.E]])
        # The exceptional point must be recomputed, not silently substituted.
        exceptional, _ = self.operation("MatrixExp", [[0, 1], [0, 0]])
        self.assertMatrixEqual(exceptional.value, [[1, 1], [0, 1]])

    def test_exponential_float_against_closed_form(self):
        outcome, _ = self.operation("MatrixExp", [[0.0, -0.5], [0.5, 0.0]])
        expected = sp.Matrix([[sp.cos(sp.Rational(1, 2)), -sp.sin(sp.Rational(1, 2))],
                              [sp.sin(sp.Rational(1, 2)), sp.cos(sp.Rational(1, 2))]])
        for error in outcome.value - expected:
            self.assertLess(abs(float(error.evalf())), 1e-14)

    def test_numeric_diagonal_and_four_by_four(self):
        outcome, _ = self.operation("Eigenvalues", sp.diag(1.0, 2.0, 3.0, 4.0))
        self.assertEqual([float(item) for item in outcome.value], [1, 2, 3, 4])

    def test_nested_lists_share_matrix_input_validation(self):
        outcome, _ = spectral_operation("MatrixExp", [sp.Tuple(sp.Tuple(0, 1), sp.Tuple(0, 0))])
        self.assertMatrixEqual(outcome.value, [[1, 1], [0, 1]])
        for invalid in ([[1, 2], [3]], [["1", 0], [0, 1]], [[True, 0], [0, 1]]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                spectral_operation("Eigenvalues", [invalid])

    def test_float_nearly_defective_basis_warns_about_condition(self):
        outcome, _ = self.operation("Eigenvectors", [[1.0, 1.0], [0.0, 1.0000000001]])
        self.assertTrue(outcome.details["basis_complete"])
        self.assertGreater(float(outcome.details["eigenvector_condition_estimate_inf"]), 1e8)
        self.assertTrue(any("condicionada" in warning for warning in outcome.warnings))

    def test_invalid_or_over_budget_input_is_controlled(self):
        inputs = [sp.zeros(0), sp.zeros(2, 3), sp.eye(5), sp.Matrix([[sp.nan]]), sp.Matrix([[sp.oo]])]
        for matrix in inputs:
            with self.subTest(matrix=matrix):
                with self.assertRaises(ValueError):
                    self.operation("Eigenvalues", matrix)
        with self.assertRaises(ValueError):
            spectral_operation("Eigenvalues", [sp.Tuple(1, 2)])
        with self.assertRaises(ValueError):
            spectral_operation("Unknown", [sp.eye(2)])


if __name__ == "__main__":
    unittest.main()
