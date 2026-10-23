"""Independent exact identities and numerical residual checks for matrix operations."""

import unittest

import sympy as sp

from mathechan.linear_algebra import bounded_binary, matrix_operation


class LinearAlgebraTests(unittest.TestCase):
    def op(self, name, *args, assumptions=sp.true):
        return matrix_operation(name, args, assumptions)

    def test_dimensions_and_rectangular_transpose(self):
        matrix = sp.ImmutableMatrix([[1, 2, 3], [4, 5, 6]])
        self.assertEqual(self.op("Dimensions", matrix)[0].value, sp.Tuple(2, 3))
        self.assertEqual(self.op("Dimensions", sp.Tuple(1, 2))[0].value, sp.Tuple(2))
        self.assertEqual(self.op("Transpose", matrix)[0].value,
                         sp.ImmutableMatrix([[1, 4], [2, 5], [3, 6]]))

    def test_dot_complex_bilinear_not_hermitian(self):
        result, _ = self.op("Dot", sp.Tuple(1, sp.I), sp.Tuple(1, sp.I))
        self.assertEqual(result.value, 0)

    def test_dot_vector_orientations(self):
        matrix = sp.ImmutableMatrix([[1, 2, 3], [4, 5, 6]])
        self.assertEqual(self.op("Dot", matrix, sp.Tuple(1, 0, -1))[0].value, sp.Tuple(-2, -2))
        self.assertEqual(self.op("Dot", sp.Tuple(1, -1), matrix)[0].value, sp.Tuple(-3, -3, -3))
        self.assertEqual(self.op("Dot", matrix, matrix.T)[0].value,
                         sp.ImmutableMatrix([[14, 32], [32, 77]]))

    def test_trace_determinant_rational_complex(self):
        matrix = sp.ImmutableMatrix([[sp.Rational(1, 2), sp.I], [2, 3]])
        self.assertEqual(self.op("Tr", matrix)[0].value, sp.Rational(7, 2))
        self.assertEqual(self.op("Det", matrix)[0].value, sp.Rational(3, 2)-2*sp.I)

    def test_inverse_exact_identity(self):
        matrix = sp.ImmutableMatrix([[2, 3], [5, 7]])
        result, requirements = self.op("Inverse", matrix)
        self.assertEqual(result.value, sp.ImmutableMatrix([[-7, 3], [5, -2]]))
        self.assertEqual(matrix*result.value, sp.eye(2))
        self.assertEqual(requirements, ())

    def test_inverse_symbolic_condition_is_executable(self):
        a = sp.Symbol("a")
        result, requirements = self.op("Inverse", sp.diag(a, 1))
        self.assertEqual(result.status, "conditional")
        self.assertEqual(requirements, (sp.Ne(a, 0),))
        self.assertIs(requirements[0].subs(a, 0), sp.false)
        self.assertEqual(self.op("Inverse", sp.diag(a, 1), assumptions=sp.Ne(a, 0))[1], ())

    def test_singular_inverse_and_negative_power_reject(self):
        singular = sp.ImmutableMatrix([[1, 2], [2, 4]])
        for name, args in [("Inverse", [singular]), ("MatrixPower", [singular, -1])]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.op(name, *args)

    def test_integer_matrix_powers(self):
        matrix = sp.ImmutableMatrix([[1, 1], [0, 1]])
        self.assertEqual(self.op("MatrixPower", matrix, 10)[0].value,
                         sp.ImmutableMatrix([[1, 10], [0, 1]]))
        self.assertEqual(self.op("MatrixPower", matrix, 0)[0].value, sp.eye(2))
        self.assertEqual(self.op("MatrixPower", matrix, -2)[0].value,
                         sp.ImmutableMatrix([[1, -2], [0, 1]]))
        for exponent in (sp.Rational(1, 2), sp.Integer(33), sp.Symbol("n")):
            with self.assertRaises(ValueError):
                self.op("MatrixPower", matrix, exponent)

    def test_rank_rectangular_and_symbolic_branch(self):
        self.assertEqual(self.op("MatrixRank", sp.ImmutableMatrix([[1, 2, 3], [2, 4, 6]]))[0].value, 1)
        a = sp.Symbol("a")
        result, requirements = self.op("MatrixRank", sp.diag(a, 1))
        self.assertEqual(result.value, 2)
        self.assertEqual(result.status, "conditional")
        self.assertEqual(requirements, (sp.Ne(a, 0),))
        self.assertEqual(self.op("MatrixRank", sp.ImmutableMatrix([[a, 1], [0, 0]]))[1], ())

    def test_linear_solve_unique_vector_and_multiple_rhs(self):
        matrix = sp.ImmutableMatrix([[2, 1], [1, -1]])
        self.assertEqual(self.op("LinearSolve", matrix, sp.Tuple(5, 1))[0].value, sp.Tuple(2, 1))
        rhs = sp.ImmutableMatrix([[5, 0], [1, 3]])
        result, _ = self.op("LinearSolve", matrix, rhs)
        self.assertEqual(matrix*result.value, rhs)

    def test_linear_solve_rectangular_unique(self):
        matrix = sp.ImmutableMatrix([[1, 0], [0, 1], [1, 1]])
        result, _ = self.op("LinearSolve", matrix, sp.Tuple(2, 3, 5))
        self.assertEqual(result.value, sp.Tuple(2, 3))
        self.assertEqual(result.details["solution_type"], "unique")

    def test_linear_solve_family_and_no_solution(self):
        matrix = sp.ImmutableMatrix([[1, 2], [2, 4]])
        result, _ = self.op("LinearSolve", matrix, sp.Tuple(3, 6))
        self.assertEqual(result.details["solution_type"], "family")
        self.assertEqual(result.status, "evaluated")
        self.assertEqual(matrix*sp.Matrix(result.value), sp.Matrix([3, 6]))
        self.assertEqual(len(result.value.atoms(sp.Dummy)), 1)
        no_solution, _ = self.op("LinearSolve", matrix, sp.Tuple(3, 7))
        self.assertIs(no_solution.value, sp.EmptySet)
        self.assertEqual(no_solution.status, "no_solution")

    def test_underdetermined_system_family(self):
        result, _ = self.op("LinearSolve", sp.ImmutableMatrix([[1, 1, 1]]), sp.Tuple(6))
        self.assertEqual(len(result.value.atoms(sp.Dummy)), 2)
        self.assertEqual(sp.simplify(sum(result.value)), 6)

    def test_linear_solve_symbolic_unique_requires_nonsingularity(self):
        a = sp.Symbol("a")
        result, requirements = self.op("LinearSolve", sp.diag(a, 1), sp.Tuple(2, 3))
        self.assertEqual(result.value, sp.Tuple(2/a, 3))
        self.assertEqual(requirements, (sp.Ne(a, 0),))
        with self.assertRaises(ValueError):
            self.op("LinearSolve", sp.ImmutableMatrix([[a, 1, 0]]), sp.Tuple(1))

    def test_float_solve_backward_error(self):
        matrix = sp.ImmutableMatrix([[sp.Float("2.0", 40), 1], [1, sp.Float("3.0", 40)]])
        result, _ = self.op("LinearSolve", matrix, sp.Tuple(4, 7))
        self.assertLess(abs(float(result.value[0])-1), 1e-14)
        self.assertLess(abs(float(result.value[1])-2), 1e-14)
        self.assertLess(float(result.details["relative_backward_error"]), 1e-35)
        self.assertIn("condition_estimate_infinity_norm", result.details)
        self.assertTrue(result.warnings)

    def test_float_ill_conditioning_is_reported(self):
        matrix = sp.diag(sp.Float(1, 40), sp.Float("1e-20", 40))
        result, _ = self.op("Inverse", matrix)
        self.assertTrue(any("mal condicionada" in warning for warning in result.warnings))

    def test_historical_basic_arithmetic_and_scalar_division(self):
        matrix = sp.ImmutableMatrix([[1, 2], [3, 4]])
        self.assertEqual(bounded_binary("+", matrix, matrix)[0].value, 2*matrix)
        self.assertEqual(bounded_binary("-", matrix, matrix)[0].value, sp.zeros(2))
        self.assertEqual(bounded_binary("*", matrix, matrix)[0].value,
                         sp.ImmutableMatrix([[7, 10], [15, 22]]))
        self.assertEqual(bounded_binary("*", sp.Integer(2), matrix)[0].value, 2*matrix)
        self.assertEqual(bounded_binary("/", matrix, sp.Integer(2))[0].value, matrix/2)
        a = sp.Symbol("a")
        self.assertEqual(bounded_binary("/", matrix, a)[1], (sp.Ne(a, 0),))

    def test_invalid_shapes_nonfinite_and_budgets(self):
        bad = [sp.zeros(9, 1), sp.zeros(0, 0), sp.Matrix([[sp.oo]]), sp.Tuple(sp.Tuple(1), sp.Tuple(2, 3))]
        for matrix in bad:
            with self.subTest(matrix=matrix), self.assertRaises(ValueError):
                self.op("Dimensions", matrix)
        for name, args in [("Dot", [sp.ones(2, 3), sp.ones(2, 2)]),
                           ("Det", [sp.ones(2, 3)]), ("Transpose", [sp.Tuple(1, 2)])]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.op(name, *args)
        with self.assertRaises(ValueError):
            bounded_binary("/", sp.eye(2), sp.eye(2))
        with self.assertRaises(ValueError):
            bounded_binary("/", sp.eye(2), sp.S.Zero)

    def test_text_is_not_sympified_and_input_complexity_is_bounded(self):
        with self.assertRaises(ValueError):
            self.op("Det", [["1"]])
        with self.assertRaises(ValueError):
            self.op("MatrixPower", sp.eye(2), "2")
        x = sp.Symbol("x")
        complex_entry = sp.Add(*(sp.sin(k*x) for k in range(1, 130)), evaluate=False)
        with self.assertRaises(ValueError):
            self.op("Det", sp.Matrix([[complex_entry]]))

    def test_vector_arithmetic_preserves_flat_shape(self):
        left, right = sp.Tuple(1, 2), sp.Tuple(3, 4)
        self.assertEqual(bounded_binary("+", left, right)[0].value, sp.Tuple(4, 6))
        self.assertEqual(bounded_binary("-", left, right)[0].value, sp.Tuple(-2, -2))
        self.assertEqual(bounded_binary("*", sp.Integer(2), left)[0].value, sp.Tuple(2, 4))
        self.assertEqual(bounded_binary("*", left, sp.Integer(-1))[0].value, sp.Tuple(-1, -2))
        self.assertEqual(bounded_binary("/", left, sp.Integer(2))[0].value,
                         sp.Tuple(sp.Rational(1, 2), 1))
        a = sp.Symbol("a")
        self.assertEqual(bounded_binary("/", left, a)[1], (sp.Ne(a, 0),))
        with self.assertRaises(ValueError):
            bounded_binary("*", left, right)
        with self.assertRaises(ValueError):
            bounded_binary("+", left, sp.Matrix([3, 4]))

    def test_matrix_vector_products_and_result_composition(self):
        matrix = sp.diag(1, 2)
        vector = sp.Tuple(2, 3)
        result, _ = bounded_binary("*", matrix, vector)
        self.assertEqual(result.value, sp.Tuple(2, 6))
        self.assertEqual(bounded_binary("*", sp.Integer(2), result.value)[0].value, sp.Tuple(4, 12))
        self.assertEqual(bounded_binary("*", vector, matrix)[0].value, sp.Tuple(2, 6))
        solution, _ = self.op("LinearSolve", matrix, sp.Tuple(2, 6))
        self.assertEqual(bounded_binary("-", solution.value, vector)[0].value, sp.Tuple(0, 0))

    def test_rank_specializes_simple_equalities(self):
        a = sp.Symbol("a")
        result, requirements = self.op("MatrixRank", sp.diag(a, 1), assumptions=sp.Eq(a, 0))
        self.assertEqual(result.value, 1)
        self.assertEqual(requirements, ())


if __name__ == "__main__":
    unittest.main()
