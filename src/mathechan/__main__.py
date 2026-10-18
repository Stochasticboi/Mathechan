"""Interfaz de consola del prototipo experimental."""

import argparse
import json
from pathlib import Path
import sys

from .kernel import MathechanError, evaluate


DEMO = (
    "1/3 + 1/6",
    "Expand[(x + 1)^3]",
    "D[Exp[-x^2], x]",
    "Plot[Exp[-x^2], {x, -3, 3}]",
)


def print_conditions(result, stream=None):
    """Keep mathematical conditions visible outside the machine-readable input."""
    if result.conditions:
        print("Condiciones / Conditions: " + "; ".join(result.conditions), file=stream)
    for warning in result.warnings:
        print("Aviso / Warning: " + warning, file=stream)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Mathechan 0.1: núcleo experimental, sin escritorio todavía.")
    parser.add_argument("expression", nargs="?", help="Expresión entre comillas")
    parser.add_argument("--demo", action="store_true", help="Ejecutar cuatro casos reproducibles")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="Emitir resultado estructurado")
    output.add_argument("--input", action="store_true", help="Emitir solo entrada reutilizable; condiciones en stderr")
    parser.add_argument("--output", type=Path, help="Guardar SVG para Plot (o el gráfico de la demo)")
    args = parser.parse_args(argv)
    if args.demo and args.expression:
        parser.error("Use una expresión o --demo, no ambos.")
    if not args.demo and not args.expression:
        parser.error("Indique una expresión o --demo.")
    try:
        sources = DEMO if args.demo else (args.expression,)
        results = [(source, evaluate(source)) for source in sources]
        if args.input and any(result.input is None for _, result in results):
            raise MathechanError("El resultado no admite entrada reutilizable dentro del lenguaje y límites actuales.")
        if args.output:
            graphs = [result for _, result in results if result.kind == "plot"]
            if not graphs:
                raise MathechanError("--output requiere un resultado Plot.")
            args.output.write_text(graphs[-1].svg, encoding="utf-8")
        if args.input:
            for _, result in results:
                print(result.input)
                print_conditions(result, stream=sys.stderr)
        elif args.json:
            payload = [{"source": source, "result": result.to_dict()} for source, result in results]
            print(json.dumps(payload if args.demo else payload[0]["result"], ensure_ascii=True, allow_nan=False))
        else:
            for source, result in results:
                if args.demo:
                    print(f"> {source}")
                print(result.text if result.kind == "expression" else f"Plot: {result.text} (201 muestras)")
                print_conditions(result)
            if args.output:
                print(f"SVG: {args.output}")
        return 0
    except (MathechanError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
