"""Cross-component acceptance cases for fundamental language semantics."""

import json
import unittest

from mathechan import MathechanError, Session, evaluate


class FundamentalLanguageContractTests(unittest.TestCase):
    def test_scalar_types_and_relations(self):
        self.assertEqual(evaluate("1/3+1/6").text, "1/2")
        self.assertEqual(evaluate("Sqrt[-1]^2").text, "-1")
        self.assertFalse(evaluate("N[Pi,40]").exact)
        for source in ("x==3", "x!=0", "x>0", "And[x>0,x<2]"):
            with self.subTest(source=source):
                json.dumps(evaluate(source).to_dict(), allow_nan=False)

    def test_domain_sensitive_refinement_and_no_leakage(self):
        generic = evaluate("Sqrt[x^2]").text
        self.assertIn("sqrt", generic)
        self.assertEqual(evaluate("Refine[Sqrt[x^2],Element[x,Reals]]").text, "Abs(x)")
        self.assertEqual(evaluate("Assuming[x>0,Sqrt[x^2]]").text, "x")
        self.assertEqual(evaluate("Sqrt[x^2]").text, generic)

    def test_conflicting_assumptions_are_not_used_to_prove_results(self):
        with self.assertRaises(MathechanError):
            evaluate("Assuming[And[x>0,x<0],Sqrt[x^2]]")

    def test_symbolic_snapshot_and_original_domain_survive_storage(self):
        session = Session()
        result = session.evaluate("f=(x^2-1)/(x-1)")
        self.assertTrue(result.conditions)
        self.assertTrue(session.evaluate("f").conditions)
        with self.assertRaises(MathechanError):
            session.evaluate("Substitute[f,x,1]")
        self.assertEqual(session.evaluate("Substitute[f,x,2]").text, "3")
        session.evaluate("x=5")
        self.assertEqual(session.evaluate("Substitute[f,x,2]").text, "3")

    def test_user_function_parameters_are_local_and_global_values_are_snapshots(self):
        session = Session()
        session.evaluate("x=10")
        session.evaluate("a=2")
        session.evaluate("Define[f,{x},a*x^2]")
        session.evaluate("a=9")
        self.assertEqual(session.evaluate("f[3]").text, "18")
        self.assertEqual(session.evaluate("x").text, "10")
        self.assertEqual(Session().evaluate("x").text, "x")

    def test_local_bindings_do_not_escape(self):
        session = Session()
        session.evaluate("x=10")
        self.assertEqual(session.evaluate("With[{x},{2},x+1]").text, "3")
        self.assertEqual(session.evaluate("x").text, "10")

    def test_persistent_hypotheses_are_confined_to_one_session(self):
        session = Session()
        session.evaluate("Assume[x>0]")
        self.assertEqual(session.evaluate("Sqrt[x^2]").text, "x")
        self.assertIn("sqrt", Session().evaluate("Sqrt[x^2]").text)
        with self.assertRaises(MathechanError):
            session.evaluate("Assume[x<0]")
        self.assertEqual(session.evaluate("Sqrt[x^2]").text, "x")
        session.evaluate("ClearAssumptions[]")
        self.assertIn("sqrt", session.evaluate("Sqrt[x^2]").text)

    def test_held_invalid_calculation_is_not_executed_on_construction(self):
        held = evaluate("Hold[1/0]")
        self.assertIn("Hold", held.text)
        with self.assertRaises(MathechanError):
            evaluate("ReleaseHold[Hold[1/0]]")

    def test_vectors_and_matrices_are_serializable_mathematical_objects(self):
        for source in ("Vector[{1,x,3}]", "Matrix[{{1,2},{3,4}}]"):
            with self.subTest(source=source):
                result = evaluate(source)
                json.dumps(result.to_dict(), allow_nan=False)
                self.assertIn(result.kind, ("vector", "matrix"))

    def test_assumptions_do_not_authorize_invalid_integration_branches(self):
        with self.assertRaises(MathechanError):
            evaluate("Integrate[Assuming[x>0,Sqrt[x^2]],{x,-1,1}]")
        self.assertEqual(
            evaluate("Integrate[Assuming[x>0,Sqrt[x^2]],{x,1,2}]").text, "3/2"
        )

    def test_solutions_excluded_by_active_assumptions_are_filtered(self):
        result = evaluate("Assuming[x>0,Solve[x^2==1,x]]")
        self.assertEqual(result.text, "{1}")
        self.assertTrue(result.conditions)

    def test_interval_validation_accepts_supported_real_hypotheses(self):
        for source, expected in (
            ("Integrate[Assuming[And[x>0,x<3],x],{x,1,2}]", "3/2"),
            ("Integrate[Assuming[Element[x,Reals],Sqrt[x^2]],{x,-1,1}]", "1"),
            ("Integrate[Assuming[Element[x,Interval[0,3]],x],{x,1,2}]", "3/2"),
        ):
            with self.subTest(source=source):
                self.assertEqual(evaluate(source).text, expected)

    def test_unresolved_infinite_families_keep_explicit_condition(self):
        result = evaluate("Assuming[x>0,Solve[Sin[x]==0,x]]")
        self.assertEqual(result.status, "unresolved")
        self.assertIn("ConditionSet", result.text)


if __name__ == "__main__":
    unittest.main()
