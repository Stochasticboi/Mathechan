"""Public linear algebra syntax, exact identities and saved domain contracts."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sympy as sp

from mathechan import Session, MathechanError, evaluate
from mathechan.kernel import Parser, build


def value(source):
    return build(Parser(source).parse())


class MatrixLanguageTests(unittest.TestCase):
    def test_basic_arithmetic_and_product_spellings(self):
        s = Session()
        s.evaluate("A=Matrix[{{1,2},{3,4}}]")
        s.evaluate("B=Matrix[{{5,6},{7,8}}]")
        for source, expected in (("A+B", [[6,8],[10,12]]), ("A-B", [[-4,-4],[-4,-4]]),
                                 ("2*A", [[2,4],[6,8]]), ("-A", [[-1,-2],[-3,-4]]),
                                 ("A/2", [[sp.Rational(1,2),1],[sp.Rational(3,2),2]]),
                                 ("A*B", [[19,22],[43,50]]), ("A.B", [[19,22],[43,50]]),
                                 ("Dot[A,B]", [[19,22],[43,50]])):
            with self.subTest(source=source):
                result = s.evaluate(source)
                self.assertEqual(result.text, sp.sstr(sp.ImmutableMatrix(expected)))
                self.assertIsNotNone(result.input)
                self.assertEqual(value(result.input), sp.ImmutableMatrix(expected))

    def test_dot_bilinear_lists_rectangular_and_decimal_tokenization(self):
        self.assertEqual(value("{1,2}.{3,4}"), 11)
        self.assertEqual(value("Dot[{Sqrt[-1],1},{Sqrt[-1],1}]"), 0)
        self.assertEqual(value("Dot[{{1,2,3},{4,5,6}},{1,0,1}]"), sp.Tuple(4,10))
        self.assertEqual(value("1.25+0.5"), sp.Rational(7,4))
        self.assertEqual(value("Dot[{{1,2}},{{3},{4}},{{2,3}}]"), sp.ImmutableMatrix([[22,33]]))
        self.assertEqual(value("2*Matrix[{{1,0},{0,2}}].{2,3}"), sp.Tuple(4,12))
        self.assertEqual(value("-Dot[{{1,0},{0,2}},{2,3}]+{2,3}"), sp.Tuple(0,-3))

    def test_matrix_functions_exact(self):
        self.assertEqual(value("Dimensions[{{1,2,3},{4,5,6}}]"), sp.Tuple(2,3))
        self.assertEqual(value("Transpose[{{1,2,3},{4,5,6}}]"), sp.ImmutableMatrix([[1,4],[2,5],[3,6]]))
        self.assertEqual(value("Tr[{{1,2},{3,4}}]"), 5)
        self.assertEqual(value("Det[{{1,2},{3,4}}]"), -2)
        self.assertEqual(value("MatrixRank[{{1,2},{2,4}}]"), 1)
        a = sp.ImmutableMatrix([[1,2],[3,4]])
        self.assertEqual(value("Inverse[{{1,2},{3,4}}]"), a.inv())
        self.assertEqual(value("MatrixPower[{{1,2},{3,4}},0]"), sp.eye(2))
        self.assertEqual(value("MatrixPower[{{1,2},{3,4}},-2]"), a.inv()**2)
        self.assertEqual(value("MatrixExp[{{0,1},{0,0}}]"), sp.ImmutableMatrix([[1,1],[0,1]]))

    def test_inverse_conditions_are_executable_and_survive_storage(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            s = Session()
            r = s.evaluate("B=Inverse[{{a,0},{0,1}}]")
            self.assertTrue(r.conditions)
            self.assertRaises(MathechanError, s.evaluate, "B/.a->0")
            path = Path(directory)/"state.json"
            s.save(path)
            with patch("mathechan.kernel.build", side_effect=AssertionError("source executed on load")):
                loaded = Session.load(path)
            self.assertRaises(MathechanError, loaded.evaluate, "B/.a->0")
            self.assertEqual(loaded.evaluate("B/.a->2").text,
                             sp.sstr(sp.diag(sp.Rational(1,2),1)))

    def test_matrix_denominator_requirements_survive_composition(self):
        self.assertRaises(MathechanError, evaluate, "(Matrix[{{x}}]/x)/.x->0")
        self.assertRaises(MathechanError, evaluate, "Tr[Inverse[{{x,0},{0,1}}]]/.x->0")

    def test_parametric_compatibility_is_preserved_with_solution_family(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            s = Session()
            result = s.evaluate("u=LinearSolve[{{1,0},{0,0}},{1,b}]")
            self.assertEqual(result.status, "conditional")
            self.assertTrue(result.conditions)
            s.evaluate("u/.b->0")
            self.assertRaises(MathechanError, s.evaluate, "u/.b->1")
            path = Path(directory)/"family.json"
            s.save(path)
            with patch("mathechan.kernel.build", side_effect=AssertionError("source executed on load")):
                loaded = Session.load(path)
            loaded.evaluate("u/.b->0")
            self.assertRaises(MathechanError, loaded.evaluate, "u/.b->1")

    def test_numerical_matrices_preserve_precision_and_solve_residual(self):
        a = value("N[Matrix[{{1,1/2},{1/3,1/4}}],50]")
        self.assertTrue(a.atoms(sp.Float))
        self.assertGreaterEqual(min(f._prec for f in a.atoms(sp.Float)), 160)
        x = value("LinearSolve[N[{{1,1/2},{1/3,1/4}},50],N[{1,2},50]]")
        x = sp.Matrix(x)
        residual = a*x-sp.Matrix([1,2])
        self.assertTrue(all(abs(z.evalf()) < 1e-45 for z in residual))
        self.assertFalse(evaluate("N[Matrix[{{1,0},{0,1}}],30]").exact)

    def test_dot_held_roundtrip_without_running_on_load(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            s = Session()
            s.evaluate("h=Hold[{{1,2}}.{{3},{4}}]")
            path = Path(directory)/"held.json"
            s.save(path)
            with patch("mathechan.kernel.build", side_effect=AssertionError("executed on load")):
                loaded = Session.load(path)
            self.assertEqual(loaded.evaluate("ReleaseHold[h]").text, sp.sstr(sp.ImmutableMatrix([[11]])))

    def test_controlled_errors_and_protected_names(self):
        for source in ("Dot[{1,2},{1}]", "Inverse[{{1,2},{2,4}}]", "Det[{{1,2}}]",
                       "MatrixExp[{{1,2}}]", "MatrixPower[{{1}},1/2]", "Matrix[{{1}}]/Matrix[{{2}}]",
                       "Matrix[{{1,2}}]+Matrix[{{1},{2}}]", "Dot[1,2]", "N[{},30]", "N[{{1}},0]"):
            with self.subTest(source=source), self.assertRaises(MathechanError):
                evaluate(source)
        for name in ("Dot", "Det", "LinearSolve", "Eigenvalues", "MatrixExp"):
            with self.subTest(name=name), self.assertRaises(MathechanError):
                Session().evaluate(name+"=1")


if __name__ == "__main__":
    unittest.main()
