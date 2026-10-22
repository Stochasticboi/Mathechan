"""Definition inspects stored numeric snapshots without evaluating its argument."""

import json
import unittest
from unittest.mock import patch

import sympy as sp

from mathechan import MathechanError, Session, evaluate
from mathechan.session import MAX_DEFINITIONS, PROTECTED_NAMES


class SessionDefinitionTests(unittest.TestCase):
    def test_defined_name_reports_the_stored_value(self):
        session = Session()
        session.evaluate("x=1/3")
        result = session.evaluate("Definition[x]")
        self.assertEqual(result.kind, "session")
        self.assertEqual(result.status, "evaluated")
        self.assertTrue(result.exact)
        self.assertIsNone(result.input)
        self.assertEqual(
            result.details,
            {"definition": {"name": "x", "defined": True, "value": "1/3", "exact": True}},
        )
        self.assertEqual(session.evaluate("x").text, "1/3")
        self.assertEqual(
            json.loads(json.dumps(result.to_dict(), allow_nan=False))["details"],
            result.details,
        )

    def test_undefined_name_does_not_create_a_definition(self):
        session = Session()
        for _ in range(2):
            result = session.evaluate("Definition[x]")
            self.assertEqual(result.details, {"definition": {"name": "x", "defined": False}})
            self.assertIsNone(result.input)
            self.assertEqual(session.evaluate("x").text, "x")
        self.assertFalse(session.evaluate("Clear[x]").details["clear"]["removed"])

    def test_inspection_uses_literal_name_and_bypasses_mathematical_evaluation(self):
        session = Session()
        session.evaluate("x=3")
        with patch("mathechan.session._evaluate_node", side_effect=AssertionError("evaluation")):
            result = session.evaluate("Definition[x]")
            missing = session.evaluate("Definition[y]")
        self.assertEqual(result.details["definition"]["value"], "3")
        self.assertFalse(missing.details["definition"]["defined"])

    def test_immediate_snapshots_and_other_sessions_are_unchanged(self):
        first, second = Session(), Session()
        first.evaluate("x=3")
        first.evaluate("a=x+1")
        first.evaluate("x=9")
        second.evaluate("x=7")
        self.assertEqual(first.evaluate("Definition[a]").details["definition"]["value"], "4")
        self.assertEqual(first.evaluate("Definition[x]").details["definition"]["value"], "9")
        self.assertEqual(second.evaluate("Definition[x]").details["definition"]["value"], "7")
        self.assertEqual(first.evaluate("a").text, "4")
        self.assertEqual(second.evaluate("x").text, "7")

    def test_approximate_value_keeps_50_digit_precision_and_inspection_status(self):
        session = Session()
        stored = session.evaluate("p=N[Pi,50]")
        expected = sp.sstr(sp.N(sp.pi, 50))
        for _ in range(2):
            result = session.evaluate("Definition[p]")
            self.assertEqual(result.details["definition"]["value"], expected)
            self.assertFalse(result.details["definition"]["exact"])
            self.assertFalse(result.exact)
            self.assertEqual(result.status, "evaluated")
            self.assertEqual(session.evaluate("p").text, stored.text)

    def test_metadata_is_detached_from_the_session(self):
        session = Session()
        session.evaluate("x=3")
        result = session.evaluate("Definition[x]")
        result.details["definition"]["value"] = "100"
        result.details["definition"]["defined"] = False
        result.details.clear()
        self.assertEqual(session.evaluate("x").text, "3")
        self.assertEqual(session.evaluate("Definition[x]").details["definition"]["value"], "3")

    def test_clear_and_reassignment_are_reflected_by_later_inspection(self):
        session = Session()
        session.evaluate("x=3")
        self.assertTrue(session.evaluate("Definition[x]").details["definition"]["defined"])
        session.evaluate("Clear[x]")
        self.assertEqual(
            session.evaluate("Definition[x]").details,
            {"definition": {"name": "x", "defined": False}},
        )
        session.evaluate("x=8")
        self.assertEqual(session.evaluate("Definition[x]").details["definition"]["value"], "8")

    def test_inspection_at_capacity_does_not_allocate_or_release_bindings(self):
        session = Session()
        for index in range(MAX_DEFINITIONS):
            session.evaluate(f"v{index}={index}")
        self.assertEqual(session.evaluate("Definition[v0]").details["definition"]["value"], "0")
        self.assertFalse(session.evaluate("Definition[missing]").details["definition"]["defined"])
        self.assertRaises(MathechanError, session.evaluate, "extra=1")
        session.evaluate("Clear[v0]")
        session.evaluate("extra=1")
        self.assertEqual(session.evaluate("Definition[extra]").details["definition"]["value"], "1")

    def test_invalid_arguments_and_nested_commands_preserve_state(self):
        session = Session()
        session.evaluate("x=3")
        for source in (
            "Definition[]", "Definition[x,y]", "Definition[3]", "Definition[x+0]",
            "Definition[{x}]", "Definition[x==3]", "Definition[Sin[x]]",
            "Definition[Clear[x]]", "Clear[Definition[x]]", "Definition[Definition[x]]",
            "x=Definition[x]", "y=Definition[x]", "1+Definition[x]",
            "{Definition[x]}", "Sum[Definition[x],{n,1,0}]",
            "D[Definition[x],x]", "Plot[Definition[x],{x,0,1}]",
            "DSolve[D[Definition[x],x]==Definition[x],Definition[x],x]",
            "Definition[x]; Clear[x]", "Definition[x] garbage",
        ):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, session.evaluate, source)
                self.assertEqual(session.evaluate("x").text, "3")
                self.assertEqual(session.evaluate("y").text, "y")

    def test_protected_names_cannot_be_inspected_or_reassigned(self):
        session = Session()
        self.assertIn("Definition", PROTECTED_NAMES)
        for name in PROTECTED_NAMES:
            with self.subTest(name=name):
                self.assertRaises(MathechanError, session.evaluate, f"Definition[{name}]")
                self.assertRaises(MathechanError, session.evaluate, f"{name}=1")
        self.assertEqual(session.evaluate("Sin[Pi/2]").text, "1")

    def test_stateless_evaluation_rejects_inspection(self):
        session = Session()
        session.evaluate("x=3")
        self.assertRaises(MathechanError, evaluate, "Definition[x]")
        self.assertEqual(session.evaluate("x").text, "3")


if __name__ == "__main__":
    unittest.main()
