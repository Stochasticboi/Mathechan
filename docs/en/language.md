# Experimental language v0

[Español](../es/lenguaje.md)

Mathechan 0.1 provides an experimental console with its own parser and
mathematical evaluation through SymPy. Its syntax follows selected Mathematica
conventions but does not provide general Wolfram Language compatibility.
There is no graphical interface or visual notebook editor yet.

## Expressions

| Element | Syntax and behavior |
|---|---|
| Integers and decimals | Exact: `0.1+0.2` produces `3/10` |
| Symbols | ASCII letters followed by letters or digits; case-sensitive |
| Constants | `Pi`, `E` |
| Operators | `+`, `-`, `*`, `/`, `^`; multiplication must be explicit |
| Grouping | Parentheses: `(x+1)^2` |
| Single-argument functions | `Sin`, `Cos`, `Exp`, `Log`, `Sqrt`, `Expand`, `Simplify` |
| Derivative | `D[expression, symbol]` |
| Plot | `Plot[expression, {symbol, minimum, maximum}]`, only at the expression root |

Powers associate to the right: `x^2^3` means `x^(2^3)`. Powers take precedence
over unary signs: `-x^2` means `-(x^2)`. Subtraction and division associate to
the left. Text results currently use SymPy notation, such as `3*x**2`;
this output is not guaranteed to be valid input for the Mathechan parser.

Assignments, patterns, user-defined functions, general lists, `Integrate`,
`Solve`, units, and stateful sessions are not supported. Symbols are not
automatically assumed real. Operations follow SymPy conventions and complex
domains unless explicitly restricted, as with `Plot`. The program does not
yet provide physical assumptions or solution steps.

## Console

The Windows executable opens an interactive console when started without
arguments. Each line is an independent expression; `exit`, `quit`, or `salir`
ends the session. Arguments run a single command:

```powershell
.\Mathechan.exe 'D[x^3,x]'
.\Mathechan.exe '1/3+1/6' --json
.\Mathechan.exe 'Plot[Exp[-x^2],{x,-3,3}]' --output gaussian.svg
.\Mathechan.exe --demo --output gaussian.svg
```

The interactive console shows a `Plot` summary; exporting SVG requires a
command with `--output`. Plot windows do not open automatically. After
installing the Python package, `python -m mathechan` accepts the same arguments;
that command requires an expression or `--demo`.

## Input and numerical limits

The parser accepts up to 4096 characters, 256 tokens, 40 syntax nesting levels,
100 characters per number, and numerical exponents with absolute value at most
1000. These restrictions do not guarantee execution time or memory limits.
Symbolic operations may take time; there is no isolation or hard timeout.

`Plot` takes 201 equally spaced samples and generates a 640×340 SVG. It requires
one free variable and a finite, increasing real range. Complex, undefined, or
non-finite float values and unrepresentable scales are rejected. Fixed sampling
may miss singularities and connect discontinuities between samples: it does
not replace scientific verification of a plot or detect every pole. SVG output
is saved at the requested path.

## Python API

`from mathechan import evaluate, MathechanError`.
`evaluate(source)` returns `EvaluationResult` with `kind`, `text`, `latex`,
`svg`, and `points`; `to_dict()` produces serializable content. Expected errors
raise `MathechanError`. The parser translates its own syntax tree into SymPy
objects without interpreting input as Python code.

## JSON notebooks v0.1

The initial extension is `.mchan`. A document has exactly `format`, `version`,
`versions`, and `cells`. `format` is `mathechan-notebook` and `version` is `0.1`.
`versions` contains the strings `kernel` and `sympy`. Each cell has a unique
`id`, `kind` (`code` or `markdown`), `source`, and `results`. Stored results only
accept objects of the form `{"kind":"text","text":"…"}`.

Opening and saving never evaluates cells or interprets markdown. Text must be
valid Unicode encodable as UTF-8. Unknown fields, duplicate ids or JSON keys,
unknown format versions, and nonstandard JSON constants are rejected. The
maximum size is 2 MB. Stored results are historical and do not prove that the
current code was executed.

API in `mathechan.notebook`: `new_notebook()`, `new_cell(source, kind="code")`,
`validate_notebook(document)`, `load_notebook(path)`, `save_notebook(document, path)`.
Embedded HTML or SVG is not supported by this initial format.
`examples/gaussian.mchan` contains source cells without cached results;
`Exp[-x^2]` alone is not a normalized probability density.
