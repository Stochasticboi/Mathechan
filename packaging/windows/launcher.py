"""Console entry point for the Windows executable."""

import sys

from mathechan import MathechanError, __version__, evaluate
from mathechan.__main__ import main as command_main, print_conditions


def repl():
    """Read one independent expression per line until an exit command or EOF."""
    print(f"Mathechan {__version__} | Consola experimental / Experimental console")
    print("Escriba una expresion / Enter an expression. Salir / Exit: exit, quit, salir")
    print("Ejemplo / Example: D[x^3,x]")
    while True:
        try:
            source = input("Mathechan> ").strip()
        except EOFError:
            print("\nHasta luego / Goodbye.")
            return 0
        if source.lower() in ("exit", "quit", "salir"):
            print("Hasta luego / Goodbye.")
            return 0
        if not source:
            continue
        try:
            result = evaluate(source)
            if result.kind == "plot":
                print(f"Plot: {result.text} ({len(result.points)} muestras / samples)")
                print("Guardar SVG / Save SVG: Mathechan.exe \"Plot[...]\" --output plot.svg")
            else:
                print(result.text)
                if result.input is not None and result.input != result.text:
                    print(f"Entrada / Input: {result.input}")
            print_conditions(result)
        except MathechanError as error:
            print(f"Error: {error}", file=sys.stderr)


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    try:
        return command_main(arguments) if arguments else repl()
    except KeyboardInterrupt:
        print("\nInterrumpido / Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
