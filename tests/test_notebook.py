"""Los cuadernos son datos; abrirlos nunca ejecuta su contenido."""

import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mathechan.notebook import (NotebookError, load_notebook, new_cell, new_notebook,
                                save_notebook, validate_notebook)


class NotebookTests(unittest.TestCase):
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
