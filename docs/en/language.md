# Experimental language v0

[Español](../es/lenguaje.md)

This document describes **Mathechan 0.1.1**. Scientific operations are included
in this version; the earlier v0.1.0 ZIP retains its original scope. Check
[release notes](releases/0.1.1.md) and [downloads](../../README.en.md) before
selecting a distribution.
The “Under development: numeric session” section describes a later increment,
without a new release; it must not be attributed to the published 0.1.1 ZIP.

Mathechan 0.1.1 provides an experimental console with its own parser and
mathematical evaluation through SymPy. Its syntax follows selected Mathematica
conventions but does not provide general Wolfram Language compatibility.
There is no graphical interface or visual notebook editor yet.

## Expressions

| Element | Syntax and behavior |
|---|---|
| Integers and decimals | Exact: `0.1+0.2` produces `3/10` |
| Symbols | ASCII letters followed by letters or digits; case-sensitive |
| Constants | `Pi`, `E`; `Infinity` in integration bounds |
| Operators | `+`, `-`, `*`, `/`, `^`; multiplication must be explicit |
| Grouping | Parentheses: `(x+1)^2` |
| Single-argument functions | `Sin`, `Cos`, `Exp`, `Log`, `Sqrt`, `Expand`, `Simplify` |
| Derivative | `D[expression, symbol]` |
| Plot | `Plot[expression, {symbol, minimum, maximum}]`, only at the expression root |
| Equality | `leftHandSide == rightHandSide`; an inert equation, not assignment |
| Lists | `{a,b,...}`; up to 64 elements per list, within parser limits |

Powers associate to the right: `x^2^3` means `x^(2^3)`. Powers take precedence
over unary signs: `-x^2` means `-(x^2)`. Subtraction and division associate to
the left. Text results currently use SymPy notation, such as `3*x**2`;
this output is not guaranteed to be valid input for the Mathechan parser.
The additive `input` field contains verified reusable input when the result fits
the supported subset and current limits; otherwise it is JSON `null` or Python
`None`. The existing `text` representation is unchanged.

`I` remains a generic symbol. The imaginary constant from `Sqrt[-1]` also has
`text: "I"`, but its `input` is `Sqrt[-1]`; the generic symbol has `input: "I"`.
Mathematical constants use `Pi` and `E`. Reuse `input` rather than automatically
copying `text`.

The printer covers integers, rationals, supported symbols, sums, products,
powers, and `Sin`, `Cos`, `Exp`, `Log`, using `^` and square brackets. Candidates
pass the parser, evaluator, and structural equality check, without an additional
global `Simplify` call. Unsupported result functions, excess tokens, and numbers
exceeding input limits yield no reusable representation. The printer does not
promise to find the shortest possible representation.

In the published 0.1.1 version, assignments, patterns, user-defined function definitions, units, and stateful
sessions are not supported. Unknown functions such as `y[x]` are used within
the bounded `DSolve` context, not as arbitrary definitions. Symbols are not
automatically assumed real. Operations follow SymPy conventions and complex
domains unless explicitly restricted, as with `Plot`. The program does not
yet provide physical assumptions or solution steps.

## Under development: numeric session

This increment adds local numeric state through the `Session` API and the
Windows interactive console. It remains under development, without a version
bump or new distribution: the v0.1.1 ZIP retains independent evaluation of
each line. The `evaluate(source)` function remains stateless and rejects `=`
assignments. `==` remains an inert equality.

A session accepts one immediate root assignment `name=expression` per call.
The value must be scalar, numeric, finite, without free symbols or pending
conditions, and unconditional. Exact numbers and Float approximations are
supported; their precision is preserved without rationalizing them or reducing
them to machine floats for storage.

```python
from mathechan import Session

session = Session()
session.evaluate("x=2")
session.evaluate("a=x+1")
session.evaluate("x=4")
print(session.evaluate("a").text)  # 3
```

`a` keeps its value at assignment time, not a formula that changes when `x` is
reassigned. Session objects are isolated. The API is also available as
`mathechan.session.Session`. Results remain `EvaluationResult`; an assignment
returns the value, not a symbolic definition. Example calls are separate;
semicolon-separated script execution is not added.

A session holds at most 64 variables; reassigning an existing one uses no extra
slot. Constants and operation names are protected, including `Pi`, `E`,
`Infinity`, `Reals`, and `Complexes`. Lists, equations, conditional
results, and symbolic assignments such as `a=y+1` with unbound `y` are rejected.
Supported functions may compute numeric values; that does not create user-defined
functions. There is no `Clear` or state persistence on disk.
Closing the console or creating another session does not restore earlier values.

### Bound variables and result context

Formal variables in `D`, `Sum`, `Integrate`, `Solve`, `DSolve`, and `Plot` shadow
same-name global values within their scope; other numeric session parameters
still apply. With `x=3`, `D[x^2,x]` returns `2*x` and `Integrate[x,x]` returns
`x**2/2`, rather than differentiating a constant or integrating the constant 3.
Use `Substitute[D[x^2,x],x,3]` to evaluate the derivative at 3. The symbolic
result of `D[x^2,x]` cannot be stored through `a=D[x^2,x]`.

Nested sum indices retain local scope. For example,
`Sum[D[n^2,n],{n,1,3}]` still returns 12; a session variable `n` does not
replace the bound index. This does not add symbolic assignments.

`input` retains its **stateless** reuse contract. Re-entering symbolic output
in a session may change it through global values: with `x=3`, `2*x` becomes 6.
To reproduce an independent expression, use stateless `evaluate` or a fresh
session and preserve conditions separately. A Plot using session parameters
only provides `input` when it can be self-contained; otherwise it is None/null.

Opening or saving a `.mchan` never evaluates cells, creates assignments, or
restores variables. Its format and text results do not become Session storage.

## Scientific operations in 0.1.1

### Approximation, algebra, and substitution

| Operation | Example | Current scope |
|---|---|---|
| `N` | `N[Pi,50]` | Numeric scalar without free symbols; 15 requested digits by default, or an integer from 1 to 1000. |
| `Factor` | `Factor[x^2-1]` | Polynomials with rational coefficients, over Q. |
| `Together` | `Together[1/x+1/(x+1)]` | Combines denominators of rational functions over Q. |
| `Cancel` | `Cancel[(x^2-1)/(x-1)]` | Cancels rational factors while retaining original exclusions as conditions. |
| `Substitute` | `Substitute[x^2+y,x,1/3]` | One exact substitution, yielding `y + 1/9`; nesting is supported. |

`N` uses strict-precision evaluation and reports an error if it cannot sustain
the requested precision. Approximate results remain `Float`, including zero;
they are not rationalized. Requesting more digits of an existing approximation
does not recover lost information. `details.numeric_evaluations` records the
requested significant digits. Output containing Float has `input: null` until
the language can preserve its approximate nature on re-entry.

Factoring and rational operations are not general `Simplify`: they currently
reject functions, Float, and irrational coefficients such as `Pi` or `Sqrt[2]`.
Preflight accepts up to eight symbols, estimated degree 256 in numerator and
denominator, and a conservative estimate of 4096 terms. It may reject input
before expansion; these bounds do not guarantee execution time.

`Substitute` preserves other symbols and transforms original restrictions.
`Substitute[x/x,x,0]` is rejected; `Substitute[x/x,x,y]` retains `y != 0`.
Only finite scalar replacement values are accepted: substituting `Infinity` is
not taking a limit, although `Integrate` accepts it as a direct bound. Substitution
does not undo earlier assumption-based simplification. Replacing a parameter
may reevaluate a pending Integral and update or remove branch conditions;
real-bound requirements are retained and transformed.

### Finite sums and integration

`Sum[n^2,{n,1,10}]` returns `385`. Bounds are exact, inclusive integers; an
empty range returns zero. Each sum allows 1000 terms and an entire evaluation
shares a 2000-term budget, including nested sums. The index is locally bound,
can shadow an outer index, and creates no session assignment. Terms are
evaluated with their restrictions: cancellation of a generic formula does not
remove an excluded term.

`Integrate[x^2,x]` returns an antiderivative **without an additive constant**.
`Integrate[Exp[-x^2],{x,-Infinity,Infinity}]` returns `sqrt(pi)`.
Definite bounds are real and independent of the variable; real infinities are
allowed. Antiderivatives may include differentiation checks in `details`;
returning a definite value alone is not a verification of that integral.

`Piecewise` results are preserved: their conditions describe **alternative
branches**, not requirements that must all hold simultaneously. An unevaluated
`Integral` retains `status: "unresolved"`. Divergent branches are flagged;
a Piecewise without pending constructs has `conditional` status.
principal values are not requested automatically. Integrand exclusions involving
the bound variable are recorded in `details.integrand_conditions`, rather than
as restrictions on a free variable of the result. This does not replace general
convergence, branch, or domain analysis.

### Equations and differential equations

`Solve[x^2==2,x]` uses `Complexes` by default;
`Solve[x^2==2,x,Reals]` restricts to real solutions. Equality `==` remains an
equation even when its sides simplify to the same expression; it is not an
assignment. Chained equalities `a==b==c` are rejected; use a list.

`Solve[{x+y==3,x-y==1},{x,y}]` returns the tuple set `{(2,1)}`.
Up to eight equations and distinct variables are supported; systems are linear.
Results may be empty, finite, parametrized, or conditional sets. Substitution
residual checks and the domain appear in `details` when performed. When rank or
degree depends on parameters, degenerate cases are not silently dropped: a
conditional result may remain unresolved. Original denominator exclusions are
applied to solutions; not every returned set is a reusable list.
A real solution family subject to external restrictions may retain `conditional`
status instead of being presented as an unconditional real set.

`DSolve[D[y[x],x]==y[x],y[x],x]` supports an ordinary equation for one dependent
function, of order 1 or 2. Higher derivatives use nested `D`. Example with data:

```text
DSolve[{D[D[y[x],x],x]+y[x]==0,y[0]==1,Substitute[D[y[x],x],x,0]==0},y[x],x]
```

One ODE and up to four initial data are accepted; incompatible or unsupported
data are rejected. This example yields `y(x)=cos(x)`. Output may retain arbitrary
constants, multiple branches, or an unresolved equation.
`details.ode_residuals` and `initial_residuals` report local checks; zero residuals
do not prove family completeness, existence/uniqueness, or a global domain.
ODE systems and partial derivatives are not supported.
Retained original exclusions are also checked at initial points; uncertainty
there is not presented as unconditional verification.

The [scientific.mchan](../../examples/scientific.mchan) notebook contains example
sources without stored results. See the
[scope decision](../decisions/002-scientific-operations.md).

## Console

The Windows executable opens an interactive console when started without
arguments. Each line is an independent expression; `exit`, `quit`, or `salir`
ends the session. Arguments run a single command:

```powershell
.\Mathechan.exe 'D[x^3,x]'
.\Mathechan.exe '1/3+1/6' --json
.\Mathechan.exe 'Sqrt[-1]' --input
.\Mathechan.exe 'Plot[Exp[-x^2],{x,-3,3}]' --output gaussian.svg
.\Mathechan.exe --demo --output gaussian.svg
```

The interactive console shows a `Plot` summary; exporting SVG requires a
command with `--output`. Plot windows do not open automatically. After
installing the Python package, `python -m mathechan` accepts the same arguments;
that command requires an expression or `--demo`.
The numeric session above belongs to the development increment: the published
0.1.1 distribution and individual commands remain stateless.

`--input` writes only reusable input to stdout and conditions/warnings to stderr.
An unavailable representation returns code 2 with a clear error. It cannot be
combined with `--json`. The interactive console adds an `Entrada / Input` line
when reusable input differs from the displayed `text`.

## Original conditions

Before simplification, the evaluator retains nonzero restrictions from explicit
division denominators and bases of powers with known negative exponents. For
example, `x/x` returns `text: "1"`, `input: "1"`, and condition `(x) != 0`;
`Simplify[(x^2-1)/(x-1)]` returns `x + 1` while retaining the condition on `x-1`.
The console displays these conditions and JSON includes a `conditions` field.
Conditions are informative text, not new comparison syntax.

Reusable input for the simplified result does not automatically encode these
restrictions. Keep `conditions` and `warnings` separately: evaluating `1` alone
cannot restore its provenance from `x/x`. For plots, `input` preserves the
validated original source, including its explicit restrictions.

This is conservative, partial tracking. It does not solve the universal domain,
determine all branch cuts, or automatically incorporate every function or
derivative domain. `Plot` checks original denominators at every sample and
rejects zeros even after cancellation: `Plot[x/x,{x,-1,1}]` fails at 0. Conditions
involving unbound parameters are also rejected when they cannot be checked.
Endpoint conditions use exact symbolic values: a `Sin[x]` denominator at endpoint
`Pi` is detected as zero before coordinates are rounded.
Zeros between samples may still be missed; there is no general pole detection
or tolerance-based near-zero criterion. See the
[results and domains decision](../decisions/001-results-and-domains.md).

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
`Session` is added only in the development increment described above.
`evaluate(source)` returns `EvaluationResult` with `kind`, `text`, `latex`,
`svg`, `points`, `input`, `conditions`, `warnings`, `status`, `exact`, and `details`;
`to_dict()` produces
serializable content with the new fields added. Expected errors
raise `MathechanError`. The parser translates its own syntax tree into SymPy
objects without interpreting input as Python code.

Fields are additive. `exact` means that the returned expression contains no
Float; it does not establish complete resolution. `status` distinguishes, among
others, `evaluated`, `approximate`, `verified`, `unverified`, `conditional`,
`unresolved`, and `no_solution`. Depending on the operation, `details` reports
method, requested precision, residuals, or checks; not every result has every
field. `conditions` retains partial necessary conditions and explicitly labelled
branch conditions. Nested operations may propagate status and warnings;
`exact: true` does not mean universal success.

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
