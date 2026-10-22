"""Clearing a definition affects only its owning session and named binding."""

import json
import unittest

from mathechan import MathechanError, Session, evaluate
from mathechan.session import MAX_DEFINITIONS, PROTECTED_NAMES


class SessionClearTests(unittest.TestCase):
    def test_clear_uses_the_name_without_evaluating_its_value(self):
        session = Session()
        session.evaluate("x=3")
        result = session.evaluate("Clear[x]")
        self.assertEqual(session.evaluate("x").text, "x")
        self.assertEqual(result.kind, "session")
        self.assertIsNone(result.input)
        self.assertEqual(result.details["clear"], {"name": "x", "removed": True})
        self.assertEqual(
            json.loads(json.dumps(result.to_dict(), allow_nan=False))["details"],
            {"clear": {"name": "x", "removed": True}},
        )

    def test_clear_of_undefined_name_is_repeatable_and_does_not_assign(self):
        session = Session()
        for _ in range(2):
            result = session.evaluate("Clear[x]")
            self.assertEqual(result.details["clear"], {"name": "x", "removed": False})
            self.assertEqual(session.evaluate("x").text, "x")
        session.evaluate("x=5")
        session.evaluate("Clear[x]")
        self.assertFalse(session.evaluate("Clear[x]").details["clear"]["removed"])

    def test_other_bindings_snapshots_and_sessions_are_unchanged(self):
        first, second = Session(), Session()
        first.evaluate("x=3")
        first.evaluate("a=x+1")
        first.evaluate("y=8")
        second.evaluate("x=7")
        first.evaluate("Clear[x]")
        self.assertEqual(first.evaluate("a").text, "4")
        self.assertEqual(first.evaluate("y").text, "8")
        self.assertEqual(second.evaluate("x").text, "7")
        first.evaluate("x=9")
        self.assertEqual(first.evaluate("a").text, "4")

    def test_clear_releases_capacity_for_one_new_binding(self):
        session = Session()
        for index in range(MAX_DEFINITIONS):
            session.evaluate(f"v{index}={index}")
        self.assertRaises(MathechanError, session.evaluate, "extra=1")
        session.evaluate("Clear[v0]")
        session.evaluate("extra=1")
        self.assertEqual(session.evaluate("extra").text, "1")
        self.assertEqual(session.evaluate("v0").text, "v0")
        self.assertRaises(MathechanError, session.evaluate, "overflow=2")

    def test_invalid_commands_leave_all_bindings_unchanged(self):
        session = Session()
        session.evaluate("x=3")
        session.evaluate("y=4")
        for source in (
            "Clear[]", "Clear[x,y]", "Clear[3]", "Clear[x+0]",
            "Clear[{x}]", "Clear[x==y]", "Clear[Sin[x]]", "Clear[Clear[x]]",
            "Clear[x]; Clear[y]", "Clear[x] garbage",
        ):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, session.evaluate, source)
                self.assertEqual(session.evaluate("x").text, "3")
                self.assertEqual(session.evaluate("y").text, "4")

    def test_nested_clear_is_rejected_before_any_evaluation(self):
        session = Session()
        session.evaluate("x=3")
        for source in (
            "x=Clear[x]", "y=Clear[x]", "1+Clear[x]", "{Clear[x]}",
            "Sin[Clear[x]]", "Sum[Clear[x],{n,1,0}]",
            "D[Clear[x],x]", "Plot[Clear[x],{x,0,1}]",
            "DSolve[D[Clear[x],x]==Clear[x],Clear[x],x]",
        ):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, session.evaluate, source)
                self.assertEqual(session.evaluate("x").text, "3")
                self.assertEqual(session.evaluate("y").text, "y")

    def test_protected_names_cannot_be_cleared_or_reassigned(self):
        session = Session()
        self.assertIn("Clear", PROTECTED_NAMES)
        for name in PROTECTED_NAMES:
            with self.subTest(name=name):
                self.assertRaises(MathechanError, session.evaluate, f"Clear[{name}]")
                self.assertRaises(MathechanError, session.evaluate, f"{name}=1")
        self.assertEqual(session.evaluate("Sin[Pi/2]").text, "1")

    def test_clearing_does_not_change_remaining_exact_or_approximate_values(self):
        session = Session()
        session.evaluate("x=2")
        session.evaluate("r=1/3")
        approximate = session.evaluate("p=N[Pi,50]")
        session.evaluate("Clear[x]")
        self.assertEqual(session.evaluate("r").text, "1/3")
        self.assertTrue(session.evaluate("r").exact)
        self.assertEqual(session.evaluate("p").text, approximate.text)
        self.assertFalse(session.evaluate("p").exact)

    def test_stateless_evaluation_cannot_clear_a_session(self):
        session = Session()
        session.evaluate("x=3")
        self.assertRaises(MathechanError, evaluate, "Clear[x]")
        self.assertEqual(session.evaluate("x").text, "3")


if __name__ == "__main__":
    unittest.main()
