"""Distribution notice failures and executable acceptance checks."""

import importlib.util
import json
import math
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    specification = importlib.util.spec_from_file_location(name, ROOT / "packaging" / "windows" / f"{name}.py")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


licenses = load_script("collect_licenses")
smoke = load_script("smoke_test")


class LicenseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.package_root = self.root / "package"
        self.package_root.mkdir()
        self.python_root = self.root / "python"
        self.python_root.mkdir()
        (self.python_root / "LICENSE.txt").write_text("Python fixture license", encoding="utf-8")
        self.destination = self.root / "collected"

    def collect(self, names):
        package = SimpleNamespace(files=[Path(name) for name in names],
                                  locate_file=lambda relative: self.package_root / relative)
        with patch.object(licenses, "distribution", return_value=package):
            licenses.collect_licenses(self.destination, names=("example",), python_prefix=self.python_root)

    def notice(self, name, content):
        (self.package_root / name).write_text(content, encoding="utf-8")

    def test_copies_every_notice_and_python_license(self):
        notices = {"LICENSE.txt": "Example license", "AUTHORS": "Example authors", "NOTICE": "Example notice"}
        for name, content in notices.items():
            self.notice(name, content)
        self.collect(notices)
        for index, (name, content) in enumerate(notices.items()):
            self.assertEqual((self.destination / "example" / f"{index:02d}-{name}").read_text(encoding="utf-8"), content)
        self.assertEqual((self.destination / "PYTHON-LICENSE.txt").read_text(encoding="utf-8"), "Python fixture license")

    def test_missing_listed_notice_fails_before_copying(self):
        self.notice("LICENSE.txt", "Example license")
        with self.assertRaisesRegex(SystemExit, "Listed notice is missing"):
            self.collect(("LICENSE.txt", "AUTHORS"))
        self.assertFalse(self.destination.exists())

    def test_authors_or_notice_alone_is_not_a_license(self):
        for name in ("AUTHORS", "NOTICE"):
            with self.subTest(name=name):
                self.notice(name, "Attribution fixture")
                with self.assertRaisesRegex(SystemExit, "No nonempty LICENSE or COPYING"):
                    self.collect((name,))

    def test_empty_license_is_rejected(self):
        self.notice("LICENSE.txt", " \n")
        with self.assertRaisesRegex(SystemExit, "No nonempty LICENSE or COPYING"):
            self.collect(("LICENSE.txt",))

    def test_missing_python_license_fails_before_copying(self):
        self.notice("COPYING", "Example terms")
        (self.python_root / "LICENSE.txt").unlink()
        with self.assertRaisesRegex(SystemExit, "Python LICENSE.txt is missing"):
            self.collect(("COPYING",))
        self.assertFalse(self.destination.exists())

    def test_copy_failure_is_fatal(self):
        self.notice("COPYING", "Example terms")
        with patch.object(licenses.shutil, "copy2", side_effect=OSError("Copy refused")):
            with self.assertRaisesRegex(SystemExit, "Cannot collect required license notices"):
                self.collect(("COPYING",))


def sine_plot():
    points = [[math.pi * index / 200, math.sin(math.pi * index / 200)] for index in range(201)]
    coordinates = " ".join(f"{40 + 2.8 * index:.3f},{280 - (240 / 1.1) * (point[1] + 0.05):.3f}"
                           for index, point in enumerate(points))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="340" viewBox="0 0 640 340">'
           f'<polyline points="{coordinates}"/></svg>')
    return {"kind": "plot", "points": points, "svg": svg}, svg


class SmokeTests(unittest.TestCase):
    def test_sessions_require_exact_snapshots_and_a_fresh_process(self):
        output = "Mathechan> 1/3\nMathechan> 2/3\nMathechan> 5\nMathechan> 2/3\nMathechan> 0\nMathechan> Mathechan> 0\nMathechan> Goodbye\n"
        valid = subprocess.CompletedProcess([], 0, output, "Error: division by zero\n")
        fresh = subprocess.CompletedProcess([], 0, "Mathechan> b\nMathechan> Goodbye\n", "")
        smoke.check_session_outputs(valid, fresh)
        wrong = subprocess.CompletedProcess([], 0, output.replace("2/3", "10"), valid.stderr)
        with self.assertRaises(smoke.SmokeTestError):
            smoke.check_session_outputs(wrong, fresh)
        leaked = subprocess.CompletedProcess([], 0, "Mathechan> 2/3\nMathechan> Goodbye\n", "")
        with self.assertRaises(smoke.SmokeTestError):
            smoke.check_session_outputs(valid, leaked)

    def test_environment_removes_external_python_paths(self):
        original = {"SystemRoot": "C:\\Windows", "Path": "C:\\Python;C:\\other", "pythonpath": "source",
                    "PYTHONHOME": "runtime", "VIRTUAL_ENV": "environment", "TEMP": "temporary"}
        clean = smoke.isolated_environment(original)
        self.assertEqual(clean["PATH"].split(";"), [str(Path("C:\\Windows") / "System32"), "C:\\Windows"])
        self.assertFalse({key.upper() for key in clean} & {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"})
        self.assertEqual(clean["TEMP"], "temporary")
        self.assertEqual(original["pythonpath"], "source")

    def test_valid_plot_and_corrupt_samples(self):
        payload, svg = sine_plot()
        smoke.check_plot(payload, svg)
        payload["points"][1][1] = math.nan
        with self.assertRaisesRegex(smoke.SmokeTestError, "nonfinite"):
            smoke.check_plot(payload, svg)

    def test_invalid_svg_and_sample_count_are_rejected(self):
        payload, svg = sine_plot()
        with self.assertRaises(smoke.SmokeTestError):
            smoke.check_plot(payload, "<svg/>")
        payload["points"].pop()
        with self.assertRaisesRegex(smoke.SmokeTestError, "201 samples"):
            smoke.check_plot(payload, svg)

    def test_interior_sine_sample_and_flat_svg_are_rejected(self):
        payload, svg = sine_plot()
        payload["points"][37][1] += 0.25
        with self.assertRaisesRegex(smoke.SmokeTestError, "Unexpected sine curve samples"):
            smoke.check_plot(payload, svg)
        payload, _ = sine_plot()
        coordinates = " ".join(f"{40 + 2.8 * index:.3f},100" for index in range(201))
        flat_svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="340" viewBox="0 0 640 340">'
                    f'<polyline points="{coordinates}"/></svg>')
        payload["svg"] = flat_svg
        with self.assertRaisesRegex(smoke.SmokeTestError, "SVG curve does not match"):
            smoke.check_plot(payload, flat_svg)

    def test_smoke_contract_and_controlled_error(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "application.exe"
            executable.write_bytes(b"fixture")
            payload, svg = sine_plot()

            def run(command, **options):
                self.assertEqual(options["env"], {"PATH": "system"})
                self.assertEqual(options["timeout"], 5)
                if len(command) == 1:
                    self.assertIn("exit", options["input"])
                    return subprocess.CompletedProcess(command, 0, "3*x**2\nGoodbye", "")
                if command[1] == "1/0":
                    return subprocess.CompletedProcess(command, 2, "", "Error: division by zero")
                if command[1].startswith("Plot["):
                    Path(command[-1]).write_text(svg, encoding="utf-8")
                    return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
                return subprocess.CompletedProcess(command, 0, json.dumps({"kind": "expression", "text": "3*x**2"}), "")

            with patch.object(smoke, "isolated_environment", return_value={"PATH": "system"}), \
                    patch.object(smoke.subprocess, "run", side_effect=run) as runner:
                self.assertEqual(len(smoke.smoke_test(executable, timeout=5)), 4)
                self.assertEqual(runner.call_count, 4)

    def test_wrong_exact_answer_and_timeout_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "application.exe"
            executable.write_bytes(b"fixture")
            with patch.object(smoke, "isolated_environment", return_value={}):
                wrong = subprocess.CompletedProcess([], 0, '{"kind":"expression","text":"x"}', "")
                with patch.object(smoke.subprocess, "run", return_value=wrong):
                    with self.assertRaisesRegex(smoke.SmokeTestError, "unexpected exact result"):
                        smoke.smoke_test(executable)
                with patch.object(smoke.subprocess, "run", side_effect=subprocess.TimeoutExpired("application", 1)):
                    with self.assertRaisesRegex(smoke.SmokeTestError, "Executable check failed"):
                        smoke.smoke_test(executable, timeout=1)


if __name__ == "__main__":
    unittest.main()
