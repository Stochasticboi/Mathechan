"""Chart syntax, geometric identities and persistent domain restrictions."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sympy as sp

from mathechan import MathechanError, Session, evaluate
from mathechan.kernel import Parser, build


class CurvilinearLanguageTests(unittest.TestCase):
    def value(self, source):
        return build(Parser(source).parse())

    def test_bare_and_quoted_chart_names(self):
        for chart in ("Spherical", '"Spherical"', "Cylindrical", '"Cylindrical"'):
            with self.subTest(chart=chart):
                self.assertEqual(self.value(f"Grad[r^2,{{r,t,p}},{chart}]"),
                                 sp.ImmutableMatrix([2*sp.Symbol("r"), 0, 0]))
        self.assertEqual(self.value('Grad[x^2,{x,y,z},"Cartesian"]'),
                         sp.ImmutableMatrix([2*sp.Symbol("x"), 0, 0]))

    def test_cartesian_vector_gradient(self):
        x, y, z = sp.symbols("x y z")
        self.assertEqual(self.value("Grad[{x*y,y*z,z*x},{x,y,z}]"),
                         sp.ImmutableMatrix([[y, x, 0], [0, z, y], [z, 0, x]]))

    def test_spherical_physical_operators(self):
        r, t = sp.symbols("r t")
        self.assertEqual(self.value("Grad[r*Cos[t],{r,t,p},Spherical]"),
                         sp.ImmutableMatrix([sp.cos(t), -sp.sin(t), 0]))
        self.assertEqual(evaluate("Div[{r,0,0},{r,t,p},Spherical]").text, "3")
        self.assertEqual(self.value("Hessian[r,{r,t,p},Spherical]"), sp.diag(0, 1/r, 1/r))
        self.assertEqual(self.value("Hessian[r^2/2,{r,t,p},Spherical]"), sp.eye(3))
        self.assertEqual(self.value("Hessian[r*Sin[t]*Cos[p],{r,t,p},Spherical]"),
                         sp.zeros(3))

    def test_cylindrical_physical_operators(self):
        r, p = sp.symbols("r p")
        self.assertEqual(self.value("Grad[r*Cos[p],{r,p,z},Cylindrical]"),
                         sp.ImmutableMatrix([sp.cos(p), -sp.sin(p), 0]))
        self.assertEqual(evaluate("Div[{r,0,z},{r,p,z},Cylindrical]").text, "3")
        self.assertEqual(self.value("Curl[{0,r,0},{r,p,z},Cylindrical]"),
                         sp.ImmutableMatrix([0, 0, 2]))
        self.assertEqual(self.value("Hessian[(r^2+z^2)/2,{r,p,z},Cylindrical]"), sp.eye(3))

    def test_jacobian_component_derivatives_and_covariant_gradient_differ(self):
        p = sp.Symbol("p")
        field = "{Cos[p],-Sin[p],0}"
        partial = self.value(f"Jacobian[{field},{{r,p,z}},Cylindrical,Components]")
        self.assertEqual(partial, sp.ImmutableMatrix([[0, -sp.sin(p), 0],
                                                    [0, -sp.cos(p), 0], [0, 0, 0]]))
        for mode in ("Orthonormal", '"Orthonormal"'):
            self.assertEqual(self.value(f"Jacobian[{field},{{r,p,z}},Cylindrical,{mode}]"),
                             sp.zeros(3))
        self.assertEqual(self.value(f"Grad[{field},{{r,p,z}},Cylindrical]"), sp.zeros(3))
        self.assertEqual(self.value("Jacobian[{r,t},{r,t,p},Spherical]"),
                         sp.ImmutableMatrix([[1, 0, 0], [0, 1, 0]]))

    def test_conditions_and_serializable_metadata(self):
        result = evaluate("Div[{r,0,0},{r,t,p},Spherical]")
        self.assertEqual(result.status, "conditional")
        self.assertTrue(result.conditions)
        self.assertEqual(result.details["coordinates"], "Spherical")
        self.assertEqual(result.details["basis"], "orthonormal")
        json.dumps(result.to_dict(), allow_nan=False)

    def test_chart_requirements_survive_replacement_even_for_constant_result(self):
        source = "Div[{r,0,0},{r,t,p},Spherical]"
        valid = evaluate(f"{source}/.{{r->2,t->Pi/2,p->0}}")
        self.assertEqual(valid.text, "3")
        for rule in ("r->0", "r->-1", "t->0", "t->Pi", "p->Sqrt[-1]",
                     "r->Sqrt[-1]", "t->Sqrt[-1]"):
            with self.subTest(rule=rule), self.assertRaises(MathechanError):
                evaluate(f"{source}/.{rule}")

    def test_cylindrical_regular_chart_excludes_axis_and_complex_coordinates(self):
        for rule in ("r->0", "r->-2", "p->Sqrt[-1]", "z->Sqrt[-1]"):
            with self.subTest(rule=rule), self.assertRaises(MathechanError):
                evaluate(f"Div[{{r,0,z}},{{r,p,z}},Cylindrical]/.{rule}")

    def test_assumptions_incompatible_with_chart_are_rejected(self):
        for assumption in ("r<=0", "r<0", "t<=0", "t>=Pi"):
            with self.subTest(assumption=assumption):
                session = Session()
                session.evaluate(f"Assume[{assumption}]")
                self.assertRaises(MathechanError, session.evaluate,
                                  "Grad[r^2,{r,t,p},Spherical]")

    def test_deferred_function_binds_after_formal_differentiation(self):
        session = Session()
        session.evaluate("DefineDelayed[f,{r},Grad[r^2,{r,t,p},Spherical]]")
        self.assertEqual(session.evaluate("f[2]").text, sp.sstr(sp.ImmutableMatrix([4, 0, 0])))
        for source in ("f[-1]", "f[0]", "f[Sqrt[-1]]"):
            with self.subTest(source=source), self.assertRaises(MathechanError):
                session.evaluate(source)

    def test_with_binding_after_differentiation_and_chart_validation(self):
        result = evaluate("With[{r,t,p},{2,Pi/2,0},Grad[r^2,{r,t,p},Spherical]]")
        self.assertEqual(result.text, sp.sstr(sp.ImmutableMatrix([4, 0, 0])))
        for radius in ("0", "-1"):
            self.assertRaises(MathechanError, evaluate,
                              f"With[{{r}},{{{radius}}},Grad[r^2,{{r,t,p}},Spherical]]")

    def test_persistence_keeps_conditions_and_never_executes_delayed_operator(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory)/"session.json"
            session = Session()
            session.evaluate("v=Div[{r,0,0},{r,t,p},Spherical]")
            session.evaluate('DefineDelayed[f,{r},Grad[r^2,{r,t,p},"Spherical"]]')
            session.save(path)
            with patch("mathechan.kernel.build", side_effect=AssertionError("stored source executed")):
                restored = Session.load(path)
            self.assertTrue(restored.evaluate("v").conditions)
            self.assertEqual(restored.evaluate("f[2]").text, sp.sstr(sp.ImmutableMatrix([4, 0, 0])))
            for source in ("v/.r->0", "v/.t->Pi", "f[-1]"):
                with self.subTest(source=source), self.assertRaises(MathechanError):
                    restored.evaluate(source)

    def test_invalid_chart_modes_dimensions_and_inputs_are_controlled(self):
        sources = (
            "Grad[r,{r,t},Spherical]", "Grad[r,{r,t,p},Unknown]",
            'Grad[r,{r,t,p},"Unknown"]', "Grad[r,{r,t,p},2]",
            "Div[{r,t},{r,t,p},Spherical]", "Hessian[{r,t,p},{r,t,p},Spherical]",
            "Jacobian[{r,t},{r,t,p},Spherical,Orthonormal]",
            "Jacobian[{r,t,p},{r,t,p},Spherical,Unknown]",
            "Grad[r,{r,t,p},Spherical,Components]", "Grad[r,{r,r,p},Spherical]",
            "Grad[True,{r,t,p},Spherical]", "Curl[r,{r,t,p},Spherical]",
        )
        for source in sources:
            with self.subTest(source=source), self.assertRaises(MathechanError):
                evaluate(source)


if __name__ == "__main__":
    unittest.main()
