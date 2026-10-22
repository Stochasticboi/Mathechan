"""Explicit deferred definitions, bounded recursion, patterns, and container values."""

import unittest

from mathechan import MathechanError, Session


class SessionExtensionTests(unittest.TestCase):
    def test_containers_and_hold_are_stored_and_inspected_without_release(self):
        session = Session()
        session.evaluate("values={1,1/3,{2,3}}")
        session.evaluate("matrix=Matrix[{{1,2},{3,4}}]")
        session.evaluate("held=Hold[1/0]")
        self.assertEqual(session.evaluate("values").kind, "list")
        self.assertEqual(session.evaluate("matrix").kind, "matrix")
        self.assertEqual(session.evaluate("held").kind, "held")
        self.assertTrue(session.evaluate("Definition[held]").details["definition"]["defined"])
        self.assertRaises(MathechanError, session.evaluate, "ReleaseHold[held]")
        self.assertEqual(session.evaluate("held").kind, "held")

    def test_container_assignment_failure_keeps_prior_value(self):
        session = Session()
        session.evaluate("values={1,2}")
        self.assertRaises(MathechanError, session.evaluate, "values={1,1/0}")
        self.assertEqual(session.evaluate("values").text, "{1,2}")

    def test_deferred_scalar_uses_current_definitions(self):
        session = Session()
        session.evaluate("SetDelayed[a,x+1]")
        session.evaluate("x=2")
        self.assertEqual(session.evaluate("a").text, "3")
        session.evaluate("x=7")
        self.assertEqual(session.evaluate("a").text, "8")
        inspected = session.evaluate("Definition[a]")
        self.assertTrue(inspected.details["definition"]["delayed"])

    def test_deferred_body_is_not_evaluated_on_declaration_or_inspection(self):
        session = Session()
        session.evaluate("SetDelayed[a,1/0]")
        self.assertTrue(session.evaluate("Definition[a]").details["definition"]["delayed"])
        self.assertRaises(MathechanError, session.evaluate, "a")
        session.evaluate("Clear[a]")
        self.assertFalse(session.evaluate("Definition[a]").details["definition"]["defined"])

    def test_deferred_function_is_lexical_and_uses_current_globals(self):
        session = Session()
        session.evaluate("x=10")
        session.evaluate("k=2")
        session.evaluate("DefineDelayed[f,{x,y},k*x+y]")
        self.assertEqual(session.evaluate("f[3,4]").text, "10")
        session.evaluate("k=3")
        self.assertEqual(session.evaluate("f[3,4]").text, "13")
        self.assertEqual(session.evaluate("x").text, "10")

    def test_recursive_factorial_and_lazy_branch(self):
        session = Session()
        session.evaluate("DefineDelayed[fac,{n},If[n==0,1,n*fac[n-1]]]")
        self.assertEqual(session.evaluate("fac[0]").text, "1")
        self.assertEqual(session.evaluate("fac[6]").text, "720")
        self.assertEqual(session.evaluate("If[True,2,1/0]").text, "2")
        self.assertEqual(session.evaluate("If[False,1/0,3]").text, "3")

    def test_recursion_and_step_budgets_are_reset_between_evaluations(self):
        session = Session()
        session.evaluate("x=5")
        session.evaluate("DefineDelayed[loop,{n},loop[n]]")
        self.assertRaisesRegex(MathechanError, "32", session.evaluate, "x=loop[1]")
        self.assertEqual(session.evaluate("x").text, "5")
        session.evaluate("SetDelayed[a,b]")
        session.evaluate("SetDelayed[b,a]")
        self.assertRaises(MathechanError, session.evaluate, "a")
        self.assertEqual(session.evaluate("2+3").text, "5")

    def test_pattern_arguments_are_explicit_and_mathematically_checked(self):
        session = Session()
        session.evaluate("DefinePattern[f,{IntegerPattern[x],RealPattern[y],ScalarPattern[z]},x+y+z]")
        self.assertEqual(session.evaluate("f[2,1/2,Sqrt[-1]]").text, "5/2 + I")
        for source in ("f[1/2,2,3]", "f[2,Sqrt[-1],3]", "f[2,3,{1,2}]", "f[2,3]"):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, session.evaluate, source)
        self.assertEqual(session.evaluate("Definition[f]").details["definition"]["patterns"],
                         ["IntegerPattern", "RealPattern", "ScalarPattern"])

    def test_pattern_recursion_and_invalid_declaration_are_atomic(self):
        session = Session()
        session.evaluate("DefinePattern[f,{IntegerPattern[n]},If[n==0,1,n*f[n-1]]]")
        self.assertEqual(session.evaluate("f[5]").text, "120")
        for source in ("DefinePattern[f,{AnyPattern[x]},x]", "DefineDelayed[f,{x,x},x]",
                       "SetDelayed[Pi,3]", "DefineDelayed[f,{x},Clear[x]]"):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, session.evaluate, source)
                self.assertEqual(session.evaluate("f[3]").text, "6")

    def test_deferred_and_functions_share_capacity(self):
        session = Session()
        for index in range(63):
            session.evaluate(f"v{index}={index}")
        session.evaluate("SetDelayed[a,1]")
        self.assertRaises(MathechanError, session.evaluate, "DefineDelayed[f,{x},x]")
        session.evaluate("Clear[a]")
        session.evaluate("DefineDelayed[f,{x},x]")
        self.assertEqual(session.evaluate("f[2]").text, "2")

    def test_deferred_global_snapshot_free_symbols_are_not_parameter_capture(self):
        session = Session()
        session.evaluate("a=x")
        session.evaluate("DefineDelayed[f,{x},a+x]")
        self.assertEqual(session.evaluate("f[2]").text, "x + 2")


if __name__ == "__main__":
    unittest.main()
