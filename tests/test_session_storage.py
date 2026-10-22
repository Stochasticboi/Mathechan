"""Typed session files preserve values and never run stored source on load."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mathechan import MathechanError, Session
from mathechan.session_storage import MAX_BYTES

ROOT = Path(__file__).resolve().parents[1]


class SessionStorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=ROOT)
        self.path = Path(self.directory.name) / "session.json"

    def tearDown(self):
        self.directory.cleanup()

    def roundtrip(self, session):
        session.save(self.path)
        return Session.load(self.path)

    def test_roundtrip_exact_complex_and_high_precision_float(self):
        session = Session()
        for source in ("r=1/3", "z=Sqrt[-1]", "p=N[Pi,100]"):
            session.evaluate(source)
        restored = self.roundtrip(session)
        for name in ("r", "z", "p"):
            self.assertEqual(restored.evaluate(name).text, session.evaluate(name).text)
            self.assertEqual(restored.evaluate(name).exact, session.evaluate(name).exact)
        original, result = session._definitions["p"].value, restored._definitions["p"].value
        self.assertEqual(original._mpf_, result._mpf_)
        self.assertEqual(original._prec, result._prec)

    def test_roundtrip_containers_and_hold(self):
        session = Session()
        for source in ("a={1,2,{3,4}}", "m=Matrix[{{1,2},{3,4}}]", "h=Hold[1/0]"):
            session.evaluate(source)
        restored = self.roundtrip(session)
        for name in ("a", "m", "h"):
            self.assertEqual(restored.evaluate(name).text, session.evaluate(name).text)
        self.assertRaises(MathechanError, restored.evaluate, "ReleaseHold[h]")

    def test_roundtrip_functions_preserves_parameter_hygiene(self):
        session = Session()
        session.evaluate("a=x")
        session.evaluate("Define[f,{x},x+a]")
        session.evaluate("Define[g,{x},x/x]")
        restored = self.roundtrip(session)
        self.assertEqual(restored.evaluate("f[2]").text, "x + 2")
        self.assertRaises(MathechanError, restored.evaluate, "g[0]")

    def test_roundtrip_domains_and_persistent_assumptions(self):
        session = Session()
        session.evaluate("a=x/x")
        session.evaluate("Assume[y>0]")
        restored = self.roundtrip(session)
        self.assertTrue(restored.evaluate("a").conditions)
        self.assertRaises(MathechanError, restored.evaluate, "Substitute[a,x,0]")
        self.assertEqual(restored.evaluate("Sqrt[y^2]").text, "y")
        self.assertRaises(MathechanError, restored.evaluate, "y=-1")

    def test_deferred_source_is_never_run_during_save_or_load(self):
        session = Session()
        session.evaluate("SetDelayed[a,1/0]")
        session.evaluate("DefineDelayed[loop,{x},loop[x]]")
        with patch("mathechan.kernel.build", side_effect=AssertionError("source executed")):
            restored = self.roundtrip(session)
        self.assertTrue(restored.evaluate("Definition[a]").details["definition"]["delayed"])
        self.assertRaises(MathechanError, restored.evaluate, "a")
        self.assertRaises(MathechanError, restored.evaluate, "loop[1]")

    def test_roundtrip_deferred_pattern_factorial(self):
        session = Session()
        session.evaluate("DefinePattern[fac,{IntegerPattern[n]},If[n==0,1,n*fac[n-1]]]")
        restored = self.roundtrip(session)
        self.assertEqual(restored.evaluate("fac[5]").text, "120")
        self.assertRaises(MathechanError, restored.evaluate, "fac[1/2]")

    def test_piecewise_partial_fraction_degeneracy_survives_roundtrip(self):
        session = Session()
        session.evaluate("f=Apart[1/(x*(x+a)),x]")
        restored = self.roundtrip(session)
        result = restored.evaluate("Substitute[f,a,0]")
        self.assertEqual(result.text, "x**(-2)")
        self.assertTrue(result.conditions)
        self.assertRaises(MathechanError, restored.evaluate, "Substitute[Substitute[f,a,0],x,0]")

    def test_loading_creates_an_independent_session(self):
        session = Session()
        session.evaluate("x=2")
        restored = self.roundtrip(session)
        restored.evaluate("x=7")
        self.assertEqual(session.evaluate("x").text, "2")

    def test_unknown_fields_versions_and_constructors_are_rejected(self):
        session = Session()
        session.evaluate("x=2")
        session.save(self.path)
        original = json.loads(self.path.read_text(encoding="utf-8"))
        cases = []
        extra = dict(original); extra["execute"] = "bad"; cases.append(extra)
        version = dict(original); version["version"] = "999"; cases.append(version)
        constructor = dict(original)
        constructor["definitions"] = {"x": {"kind": "stored", "value": {"type": "expression", "constructor": "__import__", "args": []},
                                             "restrictions": [], "requirements": [], "warnings": []}}
        cases.append(constructor)
        for document in cases:
            self.path.write_text(json.dumps(document), encoding="utf-8")
            self.assertRaises(MathechanError, Session.load, self.path)

    def test_duplicate_keys_nonstandard_numbers_and_oversize_files_rejected(self):
        for text in ('{"format":1,"format":2}', '{"format":NaN}', 'x' * (MAX_BYTES + 1)):
            self.path.write_text(text, encoding="utf-8")
            self.assertRaises(MathechanError, Session.load, self.path)

    def test_protected_names_and_impossible_float_data_rejected(self):
        session = Session()
        session.evaluate("p=N[Pi,20]")
        session.save(self.path)
        original = json.loads(self.path.read_text(encoding="utf-8"))
        bad_name = dict(original)
        bad_name["definitions"] = {"Pi": original["definitions"]["p"]}
        self.path.write_text(json.dumps(bad_name), encoding="utf-8")
        self.assertRaises(MathechanError, Session.load, self.path)
        original["definitions"]["p"]["value"]["mpf"][3] = 9999
        self.path.write_text(json.dumps(original), encoding="utf-8")
        self.assertRaises(MathechanError, Session.load, self.path)

    def test_unsupported_value_does_not_replace_existing_destination(self):
        session = Session()
        session.evaluate("x=2")
        session.save(self.path)
        before = self.path.read_bytes()
        with patch("mathechan.session_storage.Codec.encode", side_effect=ValueError("unsupported")):
            self.assertRaises(MathechanError, session.save, self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_jointly_contradictory_requirements_are_rejected(self):
        session = Session()
        session.evaluate("x=1")
        session.save(self.path)
        document = json.loads(self.path.read_text(encoding="utf-8"))
        symbol = {"type": "symbol", "name": "y"}
        zero = {"type": "integer", "value": "0"}
        document["definitions"]["x"]["requirements"] = [
            {"type": "expression", "constructor": "StrictGreaterThan", "args": [symbol, zero]},
            {"type": "expression", "constructor": "StrictLessThan", "args": [symbol, zero]},
        ]
        self.path.write_text(json.dumps(document), encoding="utf-8")
        self.assertRaises(MathechanError, Session.load, self.path)

    def test_float_precision_cannot_silently_round_serialized_mantissa(self):
        session = Session()
        session.evaluate("x=1")
        session.save(self.path)
        document = json.loads(self.path.read_text(encoding="utf-8"))
        document["definitions"]["x"]["value"] = {
            "type": "float", "mpf": [0, str(2 ** 100 + 1), 0, 101], "precision": 1,
        }
        self.path.write_text(json.dumps(document), encoding="utf-8")
        self.assertRaises(MathechanError, Session.load, self.path)

    def test_rejects_over_capacity_and_reentrant_session_commands_in_ast(self):
        session = Session()
        session.evaluate("SetDelayed[a,1]")
        session.save(self.path)
        original = json.loads(self.path.read_text(encoding="utf-8"))
        original["definitions"]["a"]["node"] = {"kind": "call", "value": "ClearAll", "children": []}
        self.path.write_text(json.dumps(original), encoding="utf-8")
        self.assertRaises(MathechanError, Session.load, self.path)
        session.save(self.path)
        original = json.loads(self.path.read_text(encoding="utf-8"))
        original["definitions"] = {f"v{index}": original["definitions"]["a"] for index in range(65)}
        self.path.write_text(json.dumps(original), encoding="utf-8")
        self.assertRaises(MathechanError, Session.load, self.path)


if __name__ == "__main__":
    unittest.main()
