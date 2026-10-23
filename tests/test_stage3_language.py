"""Scientific references and cross-feature regression tests for stage-three syntax."""

from pathlib import Path
import tempfile
import unittest

import sympy as sp

from mathechan import MathechanError, Session, evaluate
from mathechan.kernel import Parser, build


class StageThreeTests(unittest.TestCase):
    def value(self, source):
        return build(Parser(source).parse())

    def test_derivative_orders_mixed_and_gamma(self):
        self.assertEqual(evaluate("D[Sin[x],{x,3}]").text, "-cos(x)")
        self.assertEqual(evaluate("D[x^2*y^3,{x,2},y]").text, "6*y**2")
        self.assertEqual(evaluate("D[D[x^3,x],x]").text, "6*x")
        self.assertIn("polygamma", evaluate("D[Gamma[x],x]").text)
        self.assertEqual(evaluate("D[Abs[x],x]").status, "unresolved")
        for source in ("D[x,{x,-1}]", "D[x,{x,33}]", "D[x,{x,1/2}]"):
            self.assertRaises(MathechanError, evaluate, source)

    def test_vector_references(self):
        x,y,z = sp.symbols("x y z")
        self.assertEqual(self.value("Grad[x^2+y^2,{x,y}]"), sp.ImmutableMatrix([2*x,2*y]))
        self.assertEqual(self.value("Div[{x^2,y^2,z^2},{x,y,z}]"), 2*x+2*y+2*z)
        self.assertEqual(self.value("Curl[{-y,x,0},{x,y,z}]"), sp.ImmutableMatrix([0,0,2]))
        self.assertEqual(self.value("Jacobian[{x*y,x+y},{x,y}]"), sp.ImmutableMatrix([[y,x],[1,1]]))
        self.assertEqual(self.value("Hessian[x^2+y^2,{x,y}]"), 2*sp.ImmutableMatrix.eye(2))
        self.assertRaises(MathechanError, evaluate, "Curl[{x,y},{x,y}]")
        self.assertRaises(MathechanError, evaluate, "Div[{x,y},{x,y,z}]")

    def test_wolfram_series_order_and_truncation(self):
        x = sp.Symbol("x")
        result = evaluate("Series[Sin[x],{x,0,5}]")
        self.assertEqual(result.status, "series")
        self.assertFalse(result.details["global_equality"])
        self.assertEqual(self.value("Series[Sin[x],{x,0,5}]"), x-x**3/6+x**5/120+sp.O(x**6))
        self.assertEqual(evaluate("Series[Exp[x],{x,0,0}]").text, "1 + O(x)")
        self.assertEqual(evaluate("Normal[Series[Exp[x],{x,0,2}]]").status, "series")
        self.assertEqual(self.value("Normal[Series[Exp[x],{x,0,2}]]"), 1+x+x*x/2)
        self.assertEqual(evaluate("Substitute[Normal[Series[Exp[x],{x,0,2}]],x,1]").status, "series")

    def test_shifted_series_laurent_and_infinity(self):
        self.assertIn("x - 1", evaluate("Series[Exp[x],{x,1,2}]").text)
        self.assertIn("1/x", evaluate("Series[1/(x*(1-x)),{x,0,2}]").text)
        infinity = evaluate("Series[1/(x+1),{x,Infinity,2}]")
        self.assertEqual(infinity.status, "series")
        self.assertIn("O(", infinity.text)

    def test_series_parameter_degeneracy_and_hypotheses(self):
        for expression in ("Log[a+x]", "Sqrt[a+x]-Sqrt[a]"):
            source = f"Series[{expression},{{x,0,0}}]"
            result = evaluate(source)
            self.assertIn("(a) != 0", result.conditions)
            self.assertRaises(MathechanError, evaluate, f"Substitute[Normal[{source}],a,0]")
        self.assertRaises(MathechanError, evaluate, "Assuming[x<0,Series[Exp[x],{x,0,2},Right]]")
        self.assertFalse(evaluate("Series[Abs[x-1],{x,0,2}]").details["global_equality"])

    def test_series_save_load_keeps_order_and_status(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory)/"session.json"
            session = Session()
            session.evaluate("s=Series[Exp[x],{x,0,3}]")
            session.evaluate("p=Normal[Series[Sin[x],{x,0,3}]]")
            session.evaluate("asym=Series[1/(x+1),{x,Infinity,2}]")
            session.save(path)
            restored = Session.load(path)
            self.assertEqual(restored.evaluate("s").status, "series")
            self.assertIn("O(x**4)", restored.evaluate("s").text)
            self.assertEqual(restored.evaluate("p").status, "series")
            self.assertEqual(restored.evaluate("Normal[s]").status, "series")
            self.assertEqual(restored.evaluate("asym").status, "series")
            self.assertIn("oo", restored.evaluate("asym").text)

    def test_finite_products_sums_empty_and_nested(self):
        self.assertEqual(evaluate("Product[k,{k,1,5}]").text, "120")
        self.assertEqual(evaluate("Sum[j,{i,1,3},{j,1,i}]").text, "10")
        self.assertEqual(evaluate("Product[j,{i,1,3},{j,1,i}]").text, "12")
        self.assertEqual(evaluate("Product[1/0,{i,2,1}]").text, "1")
        self.assertEqual(evaluate("Sum[1/0,{i,2,1}]").text, "0")
        for source in ("Product[k/k,{k,0,1}]", "Sum[n/n,{n,0,1}]",
                       "Product[k,{k,1,1001}]"):
            self.assertRaises(MathechanError, evaluate, source)

    def test_symbolic_bounds_can_be_specialized_and_require_integer(self):
        source = "Sum[n^2,{n,1,m}]"
        self.assertEqual(evaluate(f"Substitute[{source},m,3]").text, "14")
        self.assertEqual(evaluate(f"Substitute[{source},m,0]").text, "0")
        self.assertRaises(MathechanError, evaluate, f"Substitute[{source},m,1/2]")
        nested = evaluate("Sum[j,{i,1,n},{j,2,i}]")
        self.assertFalse(any("Contains(i," in item for item in nested.conditions))

    def test_convergence_and_domain_of_infinite_aggregates(self):
        self.assertEqual(evaluate("Sum[1/n^2,{n,1,Infinity}]").text, "pi**2/6")
        self.assertEqual(evaluate("Sum[1/2^n,{n,0,Infinity}]").text, "2")
        for source in ("Sum[1/n,{n,1,Infinity}]", "Product[2,{n,1,Infinity}]"):
            result = evaluate(source)
            self.assertEqual(result.status, "divergent")
        self.assertEqual(evaluate("Sum[(n-1)/(n-1),{n,1,m}]").status, "unresolved")
        pending = "Sum[j,{i,1,n},{j,1,i/2}]"
        self.assertEqual(evaluate(pending).status, "unresolved")
        self.assertEqual(evaluate(f"Substitute[{pending},n,2]").status, "unresolved")

    def test_shared_aggregate_work_budget(self):
        self.assertRaises(MathechanError, evaluate,
                          "Sum[1,{a,1,1000}]+Sum[Sum[1,{k,1,1000}],{j,1,1000},{i,1,n}]")

    def test_iterated_integration_and_dependent_real_bounds(self):
        self.assertEqual(evaluate("Integrate[1,{x,0,1},{y,0,x}]").text, "1/2")
        self.assertEqual(evaluate("Integrate[1,{x,0,1},{y,0,Sqrt[x]}]").text, "2/3")
        result = evaluate("Integrate[1,{x,0,1},{y,0,1/(x+1)}]")
        self.assertEqual(result.text, "log(2)")
        self.assertEqual(result.conditions, ())
        self.assertTrue(result.details["integrand_conditions"])
        self.assertFalse(result.details["iterated_integration"]["fubini_conditions"] == "verified")
        for source in ("Integrate[1,{x,-1,0},{y,0,Sqrt[x]}]",
                       "Integrate[1,{x,-2,0},{y,0,1/(x+1)}]",
                       "Integrate[1,{x,0,1},{y,0,Sqrt[-1]*x}]"):
            self.assertRaises(MathechanError, evaluate, source)

    def test_parameter_branches_and_special_function_antiderivatives(self):
        result = evaluate("Integrate[Exp[-a*x],{x,0,Infinity}]")
        self.assertEqual(result.status, "unresolved")
        self.assertIn("Piecewise", result.text)
        self.assertEqual(evaluate("Substitute[Integrate[Exp[-a*x],{x,0,Infinity}],a,2]").text, "1/2")
        self.assertIn("erf", evaluate("Integrate[Exp[-x^2],x]").text)
        self.assertRaises(MathechanError, evaluate,
                          "Substitute[Substitute[Integrate[(a*x+b)/(a*x+b),x],a,0],b,0]")
        self.assertRaises(MathechanError, evaluate,
                          "Substitute[Substitute[Normal[Series[(a*x+b)/(a*x+b),{x,0,2}]],a,0],b,0]")

    def test_original_release_contract_for_odes_is_preserved(self):
        result = evaluate("DSolve[{D[y[x],x]==-2*y[x],y[0]==3},y[x],x]")
        self.assertEqual(result.status, "verified")

    def test_endpoint_values_use_outer_context_before_binding(self):
        session = Session()
        session.evaluate("n=3")
        session.evaluate("x=2")
        self.assertEqual(session.evaluate("Sum[n,{n,1,n}]").text, "6")
        self.assertEqual(session.evaluate("Product[n,{n,1,n}]").text, "6")
        self.assertEqual(session.evaluate("Integrate[x,{x,0,x}]").text, "2")
        self.assertEqual(session.evaluate("Integrate[1,{x,0,1},{y,0,x}]").text, "1/2")

    def test_local_identity_without_remainder_is_not_stored_globally(self):
        session = Session()
        session.evaluate("Assume[a>0]")
        self.assertRaises(MathechanError, session.evaluate, "s=Series[Abs[x-1],{x,0,2}]")


if __name__ == "__main__":
    unittest.main()
