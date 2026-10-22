"""Immediate symbolic snapshots, lexical function parameters, and session hypotheses."""

import unittest

from mathechan import MathechanError, Session


class SymbolicSessionTests(unittest.TestCase):
    def test_symbolic_snapshot_requires_explicit_substitution(self):
        session = Session()
        session.evaluate("a=x^2")
        session.evaluate("x=3")
        self.assertEqual(session.evaluate("a").text, "x**2")
        self.assertEqual(session.evaluate("Substitute[a,x,3]").text, "9")
        self.assertEqual(session.evaluate("Definition[a]").details["definition"]["value"], "x**2")

    def test_existing_numeric_parameters_are_captured(self):
        session = Session()
        session.evaluate("k=2")
        session.evaluate("a=k*x")
        session.evaluate("k=7")
        self.assertEqual(session.evaluate("a").text, "2*x")

    def test_cancelled_domain_is_retained_by_value_and_inspection(self):
        session = Session()
        session.evaluate("a=x/x")
        for source in ("a", "Definition[a]"):
            self.assertTrue(session.evaluate(source).conditions)
        session.evaluate("x=0")
        self.assertTrue(session.evaluate("a").conditions)
        self.assertRaises(MathechanError, session.evaluate, "Substitute[a,x,0]")

    def test_self_reference_and_mutual_alias_are_rejected_atomically(self):
        session = Session()
        self.assertRaises(MathechanError, session.evaluate, "a=a+1")
        session.evaluate("a=b")
        self.assertRaises(MathechanError, session.evaluate, "b=a")
        self.assertEqual(session.evaluate("b").text, "b")
        session.evaluate("n=3")
        session.evaluate("n=n+1")
        self.assertEqual(session.evaluate("n").text, "4")

    def test_conditional_assignment_retains_provenance(self):
        session = Session()
        session.evaluate("a=Integrate[0,{t,0,b}]")
        self.assertTrue(session.evaluate("a").conditions)
        self.assertRaises(MathechanError, session.evaluate, "Substitute[a,b,Sqrt[-1]]")

    def test_function_parameters_are_local_and_globals_are_snapshots(self):
        session = Session()
        session.evaluate("x=9")
        session.evaluate("k=2")
        session.evaluate("Define[f,{x,y},k*x^2+y]")
        session.evaluate("k=7")
        self.assertEqual(session.evaluate("f[2,3]").text, "11")
        self.assertEqual(session.evaluate("x").text, "9")
        self.assertEqual(session.evaluate("Definition[f]").details["definition"]["parameters"], ["x", "y"])
        self.assertRaises(MathechanError, session.evaluate, "f[2]")

    def test_function_derivative_integral_and_local_scope_keep_parameters(self):
        session = Session()
        session.evaluate("Define[f,{x},D[x^2,x]]")
        self.assertEqual(session.evaluate("f[3]").text, "6")
        session.evaluate("Define[g,{x},Integrate[x,x]]")
        self.assertEqual(session.evaluate("g[2]").text, "2")
        session.evaluate("Define[h,{x},With[{y},{x+1},y*x]]")
        self.assertEqual(session.evaluate("h[3]").text, "12")
        self.assertEqual(session.evaluate("D[f[x],x]").text, "2")

    def test_function_restrictions_survive_cancellation(self):
        session = Session()
        session.evaluate("Define[f,{x},x/x]")
        self.assertEqual(session.evaluate("f[2]").text, "1")
        self.assertRaises(MathechanError, session.evaluate, "f[0]")
        self.assertTrue(session.evaluate("Definition[f]").conditions)

    def test_function_redefinition_failures_preserve_old_body(self):
        session = Session()
        session.evaluate("Define[f,{x},x+1]")
        for source in ("Define[f,{x},f[x]]", "Define[f,{x,x},x]", "Define[f,{Pi},Pi]",
                       "Define[f,{x},Clear[x]]", "Define[f,{x},Infinity]"):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, session.evaluate, source)
                self.assertEqual(session.evaluate("f[2]").text, "3")

    def test_with_bindings_are_simultaneous_and_never_persistent(self):
        session = Session()
        session.evaluate("x=9")
        self.assertEqual(session.evaluate("With[{x,y},{2,x},x+y]").text, "11")
        self.assertEqual(session.evaluate("x").text, "9")
        self.assertEqual(session.evaluate("y").text, "y")
        self.assertRaises(MathechanError, session.evaluate, "With[{x,x},{1,2},x]")

    def test_assumptions_are_session_local_and_assignment_checks_are_atomic(self):
        session, other = Session(), Session()
        session.evaluate("Assume[x>0]")
        self.assertEqual(session.evaluate("Sqrt[x^2]").text, "x")
        self.assertEqual(other.evaluate("Sqrt[x^2]").text, "sqrt(x**2)")
        session.evaluate("x=2")
        self.assertRaises(MathechanError, session.evaluate, "x=-1")
        self.assertEqual(session.evaluate("x").text, "2")
        self.assertRaises(MathechanError, session.evaluate, "Assume[x<0]")
        self.assertEqual(session.evaluate("Assumptions[]").text, "x > 0")
        session.evaluate("ClearAssumptions[]")
        session.evaluate("x=-1")
        self.assertEqual(session.evaluate("x").text, "-1")

    def test_function_parameter_does_not_inherit_global_hypotheses(self):
        session = Session()
        session.evaluate("Assume[x>0]")
        session.evaluate("Define[f,{x},Sqrt[x^2]]")
        self.assertEqual(session.evaluate("f[-2]").text, "2")

    def test_snapshot_free_symbol_is_not_captured_by_same_name_parameter(self):
        session = Session()
        session.evaluate("a=x")
        session.evaluate("Define[f,{x},a]")
        self.assertEqual(session.evaluate("f[2]").text, "x")
        session.evaluate("Define[g,{x},x+a]")
        self.assertEqual(session.evaluate("g[2]").text, "x + 2")
        self.assertEqual(session.evaluate("D[g[x],x]").text, "2")
        inspected = session.evaluate("Definition[g]")
        self.assertEqual(inspected.details["definition"]["parameter_labels"], ["arg1"])
        self.assertEqual(inspected.details["definition"]["value"], "arg1 + x")

    def test_snapshot_domain_is_not_captured_by_function_parameter(self):
        session = Session()
        session.evaluate("a=x/x")
        session.evaluate("Define[f,{x},a]")
        result = session.evaluate("f[0]")
        self.assertEqual(result.text, "1")
        self.assertIn("(x) != 0", result.conditions)
        self.assertRaises(MathechanError, session.evaluate, "Substitute[f[0],x,0]")

    def test_assumption_keeps_restrictions_before_cancellation(self):
        session = Session()
        session.evaluate("Assume[x/x==1]")
        self.assertRaises(MathechanError, session.evaluate, "x=0")
        session.evaluate("x=2")
        self.assertEqual(session.evaluate("x").text, "2")

    def test_function_local_assumptions_constrain_its_arguments(self):
        session = Session()
        session.evaluate("Define[f,{x},Assuming[x>0,Sqrt[x^2]]]")
        self.assertEqual(session.evaluate("f[2]").text, "2")
        self.assertRaises(MathechanError, session.evaluate, "f[-1]")

    def test_clear_all_removes_values_and_functions_but_not_hypotheses(self):
        session = Session()
        session.evaluate("Assume[x>0]")
        session.evaluate("x=2")
        session.evaluate("Define[f,{t},t+1]")
        result = session.evaluate("ClearAll[]")
        self.assertEqual(result.details["clear_all"]["removed"], 2)
        self.assertEqual(session.evaluate("Definition[x]").details["definition"]["defined"], False)
        self.assertRaises(MathechanError, session.evaluate, "f[2]")
        self.assertEqual(session.evaluate("Assumptions[]").text, "x > 0")

    def test_functions_share_variable_capacity(self):
        session = Session()
        for index in range(63):
            session.evaluate(f"v{index}={index}")
        session.evaluate("Define[f,{x},x+1]")
        self.assertRaises(MathechanError, session.evaluate, "extra=1")
        session.evaluate("Clear[f]")
        session.evaluate("extra=1")
        self.assertEqual(session.evaluate("extra").text, "1")


if __name__ == "__main__":
    unittest.main()
