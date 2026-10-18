"""Los cuadernos son datos; abrirlos nunca ejecuta su contenido."""

import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mathechan.notebook import (MAX_BYTES, NotebookError, load_notebook, new_cell, new_notebook,
                                save_notebook, validate_notebook)


class NotebookTests(unittest.TestCase):
    def notebook_at_byte_limit(self):
        document = new_notebook()
        document["cells"] = [new_cell("x" * 100_000) for _ in range(19)]
        document["cells"][0]["source"] = "ñ" + "x" * 99_999
        document["cells"].append(new_cell(""))
        size = len((json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"))
        document["cells"][-1]["source"] = "x" * (MAX_BYTES - size)
        return document

    def test_saved_notebook_at_exact_byte_limit_can_be_reopened(self):
        document = self.notebook_at_byte_limit()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "boundary.mchan"
            save_notebook(document, path)
            content = path.read_bytes()
            self.assertEqual(len(content), MAX_BYTES)
            self.assertNotIn(b"\r\n", content)
            self.assertIn("ñ".encode("utf-8"), content)
            self.assertEqual(load_notebook(path), document)

    def test_oversized_save_leaves_existing_file_unchanged(self):
        document = self.notebook_at_byte_limit()
        document["cells"][-1]["source"] += "x"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "existing.mchan"
            path.write_bytes(b"original")
            self.assertRaises(NotebookError, save_notebook, document, path)
            self.assertEqual(path.read_bytes(), b"original")

    def test_oversized_load_checks_actual_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oversized.mchan"
            path.write_bytes(b" " * (MAX_BYTES + 1))
            with self.assertRaisesRegex(NotebookError, "2 MB"):
                load_notebook(path)

    def test_json_integer_conversion_error_is_a_notebook_error(self):
        # The decoder can raise ValueError before schema validation, depending
        # on Python's integer-conversion limit. Neither case may leak it.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "integer.mchan"
            path.write_text('{"unexpected":' + "1" * 4301 + "}", encoding="utf-8")
            with self.assertRaises(NotebookError):
                load_notebook(path)

    def test_decoder_value_error_is_normalized_without_changing_integer_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.mchan"
            path.write_text("{}", encoding="utf-8")
            with patch("mathechan.notebook.json.loads", side_effect=ValueError("integer conversion limit")):
                with self.assertRaisesRegex(NotebookError, "JSON no válido"):
                    load_notebook(path)

    def test_roundtrip_without_evaluation(self):
        document = new_notebook()
        document["cells"].append(new_cell("D[x^3,x]"))
        document["cells"].append(new_cell("__import__('os').system('never execute')"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.mchan"
            with patch("mathechan.kernel.evaluate", side_effect=AssertionError("No ejecutar")):
                save_notebook(document, path)
                loaded = load_notebook(path)
            self.assertEqual(loaded, document)
        self.assertEqual(loaded["cells"][0]["results"], [])

    def test_rejects_schema_and_duplicate_ids(self):
        document = new_notebook()
        document["cells"] = [new_cell("x")]
        document["cells"].append(dict(document["cells"][0]))
        self.assertRaises(NotebookError, validate_notebook, document)
        document = new_notebook()
        document["executeOnOpen"] = True
        self.assertRaises(NotebookError, validate_notebook, document)
        document = new_notebook()
        document["version"] = "999"
        self.assertRaises(NotebookError, validate_notebook, document)

    def test_rejects_nontext_results(self):
        document = new_notebook()
        document["cells"] = [new_cell("x")]
        document["cells"][0]["results"] = [{"kind": "html", "text": "<script/>"}]
        self.assertRaises(NotebookError, validate_notebook, document)

    def test_rejects_json_duplicates_and_nonstandard_constants(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.mchan"
            for content in ('{"version":"0.1","version":"0.2"}', '{"x":NaN}', "not JSON"):
                with self.subTest(content=content):
                    path.write_text(content, encoding="utf-8")
                    self.assertRaises(NotebookError, load_notebook, path)

    def test_checked_example(self):
        path = Path(__file__).resolve().parents[1] / "examples" / "gaussian.mchan"
        notebook = load_notebook(path)
        self.assertEqual(len(notebook["cells"]), 3)

    def test_rejects_unicode_surrogates_in_load_validate_and_save(self):
        template = new_notebook()
        template["cells"] = [new_cell("x")]
        template["cells"][0]["results"] = [{"kind": "text", "text": "resultado"}]
        paths = (("cells", 0, "source"), ("cells", 0, "id"),
                 ("versions", "kernel"), ("versions", "sympy"),
                 ("cells", 0, "results", 0, "text"))
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "invalid.mchan"
            destination = Path(directory) / "existing.mchan"
            for field_path in paths:
                for surrogate in ("\ud800", "\udfff"):
                    with self.subTest(field=field_path, surrogate=repr(surrogate)):
                        document = deepcopy(template)
                        target = document
                        for key in field_path[:-1]:
                            target = target[key]
                        target[field_path[-1]] = surrogate
                        self.assertRaises(NotebookError, validate_notebook, document)
                        source.write_text(json.dumps(document, ensure_ascii=True), encoding="utf-8")
                        self.assertRaises(NotebookError, load_notebook, source)
                        destination.write_text("original", encoding="utf-8")
                        self.assertRaises(NotebookError, save_notebook, document, destination)
                        self.assertEqual(destination.read_text(encoding="utf-8"), "original")

    def test_valid_unicode_roundtrip_including_escaped_surrogate_pair(self):
        document = new_notebook()
        document["cells"] = [new_cell("Entropía: S = −Σ pᵢ log pᵢ; α, β, 🚀", kind="markdown")]
        document["cells"][0]["id"] = "celda-α"
        document["cells"][0]["results"] = [{"kind": "text", "text": "Resultado: ∞, ñ, 🚀"}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unicode.mchan"
            path.write_text(json.dumps(document, ensure_ascii=True), encoding="utf-8")
            loaded = load_notebook(path)
            self.assertEqual(loaded, document)
            save_notebook(loaded, path)
            self.assertEqual(load_notebook(path), document)
            self.assertIn("🚀", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
