"""Exercise the standalone launcher through subprocesses."""

import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "packaging" / "windows" / "launcher.py"


class LauncherTests(unittest.TestCase):
    def run_launcher(self, *arguments, input_text=""):
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run([sys.executable, str(LAUNCHER), *arguments], input=input_text,
                              capture_output=True, text=True, env=environment, timeout=30)

    def test_expression_argument(self):
        result = self.run_launcher("D[x^3,x]")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "3*x**2")

    def test_help_argument(self):
        result = self.run_launcher("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--output", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_repl_calculation_and_exit_commands(self):
        for command in ("exit", "quit", "salir"):
            with self.subTest(command=command):
                result = self.run_launcher(input_text=f"\nD[x^3,x]\n{command}\n")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Experimental console", result.stdout)
                self.assertIn("3*x**2", result.stdout)
                self.assertIn("Goodbye", result.stdout)
                self.assertNotIn("Traceback", result.stderr)

    def test_repl_eof_exits_cleanly(self):
        result = self.run_launcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Goodbye", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_input_argument_keeps_imaginary_constant_reusable(self):
        result = self.run_launcher("Sqrt[-1]", "--input")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "Sqrt[-1]")

    def test_repl_displays_reusable_input_and_original_conditions(self):
        result = self.run_launcher(input_text="Sqrt[-1]\nx/x\nsalir\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Entrada / Input: Sqrt[-1]", result.stdout)
        self.assertIn("Condiciones / Conditions: (x) != 0", result.stdout)

    def test_errors_do_not_print_tracebacks(self):
        result = self.run_launcher("1/0")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        result = self.run_launcher(input_text="1/0\nD[x^3,x]\nsalir\n")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Error:", result.stderr)
        self.assertIn("3*x**2", result.stdout)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
