# Experimental language v0

[Español](../es/lenguaje.md)

This document describes **0.2.0.dev3 source**. The published **0.2.0-dev0**
download includes sessions and extended algebra, but not dev1 limits, dev2
calculus and replacement extensions, or dev3 curvilinear charts. Historical 0.1.1 sections record the scope
of that earlier version. Check [downloads](../../README.en.md) before choosing
a distribution.

Mathechan provides an experimental console with its own parser and
mathematical evaluation through SymPy. Its syntax follows selected Mathematica
conventions but does not provide general Wolfram Language compatibility.
There is no graphical interface or visual notebook editor yet.

## Expressions

| Element | Syntax and behavior |
|---|---|
| Integers and decimals | Exact: `0.1+0.2` produces `3/10` |
| Symbols | ASCII letters followed by letters or digits; case-sensitive |
| Constants | `Pi`, `E`; `Infinity` in ranges, limits and series |
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

## Calculus and rules: development 0.2.0.dev3

This section describes current source after the 0.2.0-dev0 ZIP. Similar syntax
does not imply full Wolfram language or evaluation compatibility.

### Replacement rules

```wolfram
(x^2+a*x) /. x -> 2
ReplaceAll[x^2+a*x,Rule[x,2]]
Substitute[x^2+a*x,{x->2}]
```

All yield `4+2*a`. The original `Substitute[expr,x,value]` retains its bound-name
behaviour. `ReplaceAll` evaluates its expression and rules in the session;
existing assignments can change the parts available to replace, and an immediate
rule's left side is evaluated too.

Rules in a list act in one pass: `{x,y}/.{x->y,y->2}` yields `{y,2}`. The first
matching rule wins and inserted results are not revisited. Chain calls for
successive steps: `x/.x->y/.y->2` yields `2`. Exact parts, lists, matrices and
equations are supported within current types. Head replacement, complete
attribute-based matching and `//.` are not implemented.

Rules can be stored: `r=x->a` captures the current value; `r=x:>a`
(`RuleDelayed`) evaluates the right side on application. Loading a session
never runs a delayed body.

```wolfram
Sin[x]+Sin[y] /. Sin[t_] -> t^2
{2,1/2,z} /. t_Integer :> t+1
{N[1/2,20],1/2} /. t_Real -> 0
```

Named patterns are bounded to scalars: `t_`/`t_Scalar`, exact integers
`t_Integer`, and approximate Float numbers `t_Real`. The latter differs from
the existing `RealPattern` helper, which tests mathematical realness. Literal
`0.5` remains an exact rational; `N[1/2,20]` is Float. Anonymous blanks,
sequence patterns and pattern conditions are unsupported. At most eight
patterns and 64 rules per call; protected names cannot name pattern parameters.

Original exclusions and assumptions are transformed as well. `x/x/.x->0` and
`Assuming[x>0,Sqrt[x^2]/.x->-1]` are rejected even after simplification.
`ReplaceAll` does not rewrite retained bound operators or `O` remainders;
substitute parameters before computation, use `Substitute` where applicable,
or explicitly extract `Normal`.

### Derivatives and vector calculus

```wolfram
D[Sin[x],{x,3}]
D[x^2*y^3,{x,2},y]
Grad[x^2+y^2,{x,y}]
Div[{x^2,y^2,z^2},{x,y,z}]
Curl[{-y,x,0},{x,y,z}]
Jacobian[{x*y,x+y},{x,y}]
Hessian[x^2+y^2,{x,y}]
```

Supports successive/mixed positive derivative orders totalling at most 32,
symbolic parameters and currently exposed functions. Symbols are not assumed
real; some `Abs` derivatives remain formal. Domain restrictions survive;
global differentiability is not certified.

Without a third argument, operators use `Cartesian` with one to eight variables.
`Curl` requires three components and variables. `Grad`, `Curl`, `Jacobian` and
`Hessian` return immutable matrices; `Div` returns a scalar. Dimensions are
checked: at most 64 output elements/4096 operations and 256 input operations/
eight symbols. General matrix algebra is not added.

The third argument selects `Cartesian`, `Cylindrical` or `Spherical`, as a name
or string (`Spherical` and `"Spherical"` are equivalent). Curvilinear charts
are three-dimensional:

| Chart | Variables, in order | Regular domain |
|---|---|---|
| `Cylindrical` | `{rho,phi,z}`: radius, azimuth, height | Real coordinates, `rho>0`. |
| `Spherical` | `{r,theta,phi}`: radius, polar angle from +z, azimuth | Real coordinates, `r>0`, `0<theta<Pi`. |

Azimuth is a local real coordinate without an imposed periodic cut. Input and
output vectors use the **local orthonormal basis**, rather than the coordinate
basis. Vector `Grad` returns the covariant gradient matrix: row i is the
component and column j the orthonormal derivative direction. `Hessian` returns
the geometric Hessian in that basis, including basis variation; it is not the
array of raw second partial derivatives.

```wolfram
Grad[r^2,{r,theta,phi},"Spherical"]             (* {2*r,0,0} *)
Div[{rho,0,z},{rho,phi,z},Cylindrical]          (* 3 *)
Curl[{0,rho,0},{rho,phi,z},"Cylindrical"]      (* {0,0,2} *)
Hessian[r^2/2,{r,theta,phi},Spherical]          (* 3x3 identity *)
Jacobian[{r,0,0},{r,theta,phi},Spherical]      (* diagonal {1,0,0} *)
Jacobian[{r,0,0},{r,theta,phi},Spherical,"Orthonormal"]
(* 3x3 identity, equal to Grad of the same field *)
```

`Jacobian` defaults to `Components`: ordinary partial derivatives of component
functions with respect to the variables, including rectangular output.
The fourth argument `Orthonormal` requires three field components and returns
the geometric 3x3 vector gradient. It does not automatically reinterpret a
coordinate map as a physical field.

Chart requirements stay attached even when the result simplifies to a constant
and are checked after replacement. Axes and the origin lie outside the regular
domain; a finite simplified expression does not certify extension to those
points. Arbitrary charts and higher-rank tensors are unsupported.

### Local series

```wolfram
Series[Sin[x],{x,0,5}]
Series[Exp[x],{x,1,2}]
Series[1/(x+1),{x,Infinity,2}]
Normal[Series[Exp[x],{x,0,2}]]
```

Order n includes degree n: the first result is
`x-x^3/6+x^5/120+O(x^6)`. Orders 0–31, numerical real centres and ±Infinity
are supported. An optional `Left`/`Right` argument selects the real path;
infinity fixes its orientation. Taylor/Maclaurin, basic Laurent/Puiseux and
asymptotic expansions are returned when determined by the backend. No
convergence radius is guaranteed.

`status=series` retains local, truncated meaning. `exact=true` only describes
the absence of Float, not a certified numerical remainder bound. `Normal`
explicitly removes `O` while retaining approximation warnings and provenance;
it does not prove global equality. Series and their orders, including at
infinity, can be saved in sessions. A remainder-free identity valid only
locally with an undetermined neighbourhood cannot be stored as a global
definition. Parameter degeneracies retain explicit exclusions; substitute
parameters before expanding to study another branch. Failures stay unresolved.

### Extended aggregates

```wolfram
Product[k,{k,1,5}]
Sum[n^2,{n,1,m}]
Sum[j,{i,1,3},{j,1,i}]
Sum[1/n^2,{n,1,Infinity}]
Sum[q^n,{n,0,Infinity}]
```

Determined examples yield `120`, an expression conditional on integer m,
`10`, and `Pi^2/6`; the geometric series retains convergence conditions and a
pending branch. Up to three ranges, outermost first. Inner bounds may depend
on outer indices when their integrality can be checked. Bound names ignore
same-named session assignments.

Reversed finite ranges remain empty: sum 0 and product 1, preserving Mathechan's
previous convention rather than Karr's. Limits remain 1000 terms per range and
2000 total, shared by nested calls and rules. Symbolic finite bounds require
integers. Infinite convergence must be determined; divergent or undecidable
requests stay inert, without scalar infinities. Infinite products use the
finite nonzero convergence convention: partial products tending to zero are
reported as divergent. Unverified summand domains remain pending; undefined
terms are not silently cancelled.

### Iterated integration

`Integrate` retains indefinite, definite and improper integrals, parameters,
and backend-supported special-function results. `Integrate[Exp[-x^2],x]`, for
example, produces `erf` even though it has no public reusable input call yet.

```wolfram
Integrate[x*y,x,y]
Integrate[1,{x,0,1},{y,0,x}]
Integrate[1,{x,0,1},{y,0,Sqrt[x]}]
Integrate[Exp[-a*x],{x,0,Infinity}]
```

At most three distinct variables, outermost range first. Dependent bounds must
be real and defined throughout the outer interval; unverifiable regions are
conservatively rejected. The square-root example yields `2/3`; an outer range
[-1,0] is rejected. Fubini conditions and interchange of integration order are
not certified. Antiderivatives omit additive constants. Parameter conditions
and pending branches remain explicit; no automatic numerical fallback is used.

Budgets are structural, not effective execution-time/memory limits or scaling
guarantees. No graphical interface or later-stage specialised physics tools
are added by this increment.

## Under development: language and sessions

The `Session` API and Windows interactive console provide local state from
0.2.0.dev0 onward. The earlier v0.1.1 ZIP retains its original scope. The `evaluate(source)` function remains stateless and rejects `=`
assignments. `==` remains an inert equality.

A session accepts one immediate root assignment `name=expression` per call.
Values may be numeric or symbolic scalars and retain their original
restrictions. Exact numbers and Float approximations are supported; their
precision is preserved without rationalizing them or reducing them to machine floats.

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

A session holds at most 64 definitions; reassigning an existing one uses no extra
slot. Constants and operation names are protected, including `Pi`, `E`,
`Infinity`, `Reals`, and `Complexes`. Scalars, lists, matrices and held expressions
can be stored; equations and unverified results are rejected. An assignment
such as `a=y+1` stores the expression computed at assignment time. Closing the
console does not save variables automatically.

`session.save("work.json")` explicitly saves state; `Session.load("work.json")`
creates another session from that file. The versioned `mathechan-session` v0.1
format retains definitions, conditions and exact Float bits, with a 2 MB and
64-definition limit. Unknown fields, duplicate keys and unsupported constructors
are rejected. Loading does not execute deferred syntax trees or `Hold` contents.
It uses neither pickle nor interpretation of strings as code. This is separate
from the `.mchan` notebook format.

`session.evaluate("Clear[x]")` removes only the definition of `x` from that
session and frees its slot; evaluating `x` again returns the symbol. The name is
held without substituting its value. Previously computed values of other
variables remain unchanged: after `x=2`, `a=x+1`, and `Clear[x]`, `a` is still 3.
An undefined name leaves the session unchanged.

`Clear` requires one variable name and is accepted only as a standalone session
command. Constants and operation names, including `Clear`, are protected.
Arguments such as `Clear[x+1]`, multiple names, or nested calls are rejected
without removing values. The result has `kind: "session"`, `input: null`, and
`details.clear` containing `name` and the boolean `removed`; its text is a
confirmation rather than a mathematical expression. Stateless
`evaluate("Clear[x]")` is unsupported. `ClearAll[]` removes session definitions;
assumptions are managed separately with `ClearAssumptions[]`.

`session.evaluate("Definition[x]")` inspects the stored value of `x` without
evaluating it again or changing the session. For example, after `x=2`,
`a=x+1`, and `x=4`, `Definition[a]` displays `a = 3`, not the original formula.
An undefined name is reported without creating a definition; after `Clear[x]`,
`Definition[x]` reports that no definition exists.

The query requires one unevaluated name and is accepted only as a standalone
session command. Protected names, including `Definition`, compound arguments,
and nested calls are rejected. Stateless `evaluate` does not support this query.
It does not list variables or describe built-in functions. Results have
`kind: "session"`, `input: null`, and `details.definition` with `name` and
`defined`; a defined value adds `value` (text) and `exact` (boolean).
The result retains the stored value's exact/approximate distinction and digits;
`status: "evaluated"` means the query completed. Neither `text` nor `value` is
guaranteed reusable input. The query provides no history and does not restore
values from other sessions.

### Symbolic definitions and functions

Assignments store computed expressions, not delayed rules. After `f=x^2` and
then `x=3`, `f` retains `x^2`. Use `Substitute[f,x,3]` to evaluate it at a point.
Original restrictions accompany stored definitions: storing `f=x/x` does not
allow `Substitute[f,x,0]` later.

`Define[f,{x,y},a*x+y]` defines a function with distinct local parameters.
Available global values, such as `a`, are captured at definition time. Call it
with `f[2,3]`.
`With[{x,y},{2,3},x+y]` uses simultaneous local bindings without modifying the
session. This is not the full Wolfram Language syntax.

`SetDelayed[a,x+1]` stores an expression using the current state when `a` is
requested. `DefineDelayed[f,{x},expression]` does the same for a function.
`DefinePattern[f,{IntegerPattern[n]},If[n<=1,1,n*f[n-1]]]` permits bounded
recursion with an integer argument. `RealPattern` and `ScalarPattern` are also
supported; there is one definition per name, without overloads or arbitrary
patterns. `If[condition,yes,no]` evaluates only the selected branch; an undecided
condition retains the call. Each evaluation allows 32 nested deferred calls and
10000 steps; exceeding those limits raises a controlled error.

When a parameter and a captured symbol share a name, `Definition` uses distinct
display labels. For example, `a=x` followed by `Define[g,{x},x+a]` preserves the
free `x` from `a`: `g[2]` gives `x+2`. Inspection displays
`g[arg1] = arg1 + x`; `parameters` retains the original name and
`parameter_labels` records its display label.

### Assumptions and logic

Relations include `==`, `!=`, `<`, `<=`, `>` and `>=`; logical operations are
`And`, `Or`, `Not`, with `True` and `False`. Conditions do not assign values.
Use `Element[x,Reals]`, `Complexes`, `Integers`, or
`Element[x,Interval[0,1]]` for membership in a closed real interval.

`Assuming[condition,expression]`, `Refine[expression,condition]`, and
`Simplify[expression,condition]` use local assumptions. For example,
`Refine[Sqrt[x^2],Element[x,Reals]]` gives `Abs(x)` and
`Assuming[x>0,Sqrt[x^2]]` gives `x`; without assumptions, the square root is not
replaced by `x`. Necessary conditions remain attached to the result.

In a session, `Assume[x>0]` adds an assumption in memory, `Assumptions[]`
inspects it, and `ClearAssumptions[]` clears it. Other sessions are independent.
Simple contradictions are rejected before changing state. Consistency of
general multivariate or transcendental conditions is not fully decidable by
this implementation: unresolved assumptions remain conditions, not proven facts.

Plots check assumptions at every sample and reject conditions they cannot
validate. Definite integrals do not use an assumption-dependent branch unless
its hypotheses can be checked throughout the interval. `Solve` filters finite
candidates excluded by assumptions; unverified families retain conditions or
remain unresolved.

### Containers, held expressions and precision

`Vector[{1,x,3}]` represents a column vector and `Matrix[{{1,2},{3,4}}]`
an immutable rectangular matrix, with at most 64 scalar elements. Lists remain
lists; general matrix algebra belongs to a later stage. `Hold[1/0]` keeps the
syntax tree without performing the division; `ReleaseHold[Hold[1/0]]` attempts
evaluation and detects the error.

`Display[Pi,8]` changes presentation text while retaining the exact value.
`N[Pi,50]` computes an approximation at the requested precision.
`NumericError[Pi,20]` compares evaluations at 20 and 30 digits and reports an
absolute-difference estimate, **not a certified bound**. Increasing precision
cannot recover information lost in approximate input data.

`Log`, `Sqrt`, `ArcSin`, `ArcCos`, and `ArcTan` use principal complex branches.
Known exclusions include zero for `Log`, ±i for `ArcTan`, and nonpositive
integer poles for `Gamma`. Warnings identify the partial scope of domain
tracking: not all branch cuts, domains or composite singularities are certified.

`AnalyzeDomain[expression,x,Reals]` queries real-valued continuity with original
exclusions. With `Complexes`, it reports finite values and known branch cuts
without claiming a global holomorphic domain. `details.complete` distinguishes
determined cases from unresolved ones. `CertifiedN[Sqrt[2],40]` provides a rational
enclosure and an absolute bound relative to the returned Float, certified by exact
polynomial isolation. It accepts exact real algebraic constants only, degree up
to 32 and 10–200 digits; it does not certify `Pi`, Float data or experimental uncertainty.

`FullSimplify[expression]` and `FullSimplify[expression,assumptions]` compare
simplification, rational combination and trigonometric candidates, checking
equivalence in the specified context. Limits are 256 operations and eight symbols;
there is no universal minimal-form guarantee. Original restrictions accompany
results and stored definitions.

### Algebra under development: Collect and Apart

These operations belong to the development code, not the v0.1.1 ZIP.

| Operation | Example | Scope |
|---|---|---|
| `Collect[expression,x]` | `Collect[a*x+b*x+x^2,x]` | Groups powers of `x`, expanding a bounded polynomial over Q. |
| `Apart[expression,x]` | `Apart[1/(x*(x+1)),x]` | Rational partial fractions in `x`, with symbolic parameters. |

They reuse rational algebra limits: at most eight symbols, degree 256, and an
estimated expansion of 4096 terms. Float coefficients and transcendental
functions are unsupported. The explicit variable shadows its session value;
original restrictions and nested iterator scopes are preserved.

Parametric decompositions may require additional conditions.
`Apart[1/(x*(x+a)),x]` introduces `1/a` factors: it retains both `a!=0` and
`a=0`, whose result is `1/x^2`, using `Piecewise`. Automatic branching covers
one affine degeneracy of one parameter. Larger cases retain explicit exclusions
and require separate branch analysis.

### Algebra under development: NSolve

`NSolve[equation,x]` approximates solutions of one polynomial or rational equation
with algebraic or Float coefficients. Defaults are `Complexes` and 30 requested
digits. Supported forms also include `NSolve[x^2==2,x,50]`,
`NSolve[x^2==-1,x,Reals]`, and `NSolve[x^2==2,x,Reals,50]`.

This increment accepts numerator degree up to 32 and integer precision from
10 to 200 digits, retaining the algebra growth limits. Float data retain their
original precision: more computation digits cannot recover lost information.
Decimal literals remain exact rationals.
`NSolve[{x^2+y^2==1,x-y==0},{x,y},Reals,40]` accepts polynomial systems of up to
eight variables and equations, with total degree up to eight. Continuous
families are not replaced with artificial point lists.

`NSolve[Cos[x]==x,x,{1},40]` requests a local search from initial point 1. Supply
one initial value per variable for systems; the form
`NSolve[equations,variables,Reals,40,{initials}]` also sets the domain.
Results carry `completeness: false`: small residuals do not prove that all roots
were found or establish global uniqueness. Free parameters remain conditional
or require values before a numerical search.

Exact polynomial roots are isolated first; domain, original exclusions, and
assumptions are checked before approximation. Results include multiplicities
and residual diagnostics. A small normalized residual is a numerical check,
not a certified root-error bound or a guarantee of good conditioning.
Undecided conditions and approximations failing the checks are identified
explicitly. Identities do not produce a fictitious finite root list: they
retain the corresponding solution set or an unresolved conditioned set.

Approximations have `input: null`; their text is not advertised as reusable
exact input. `NSolve` belongs to the development code, not the published
v0.1.1 ZIP.

`Solve` also accepts bounded nonlinear polynomial systems and verifies candidates
by substitution. With symbolic degree-one or degree-two coefficients,
`details.branches` separates vanishing leading coefficients, generic solutions,
identities and contradictions; the global solution set retains its conditions.
`Reduce[condition,x,Reals]` reduces univariate conditions and preserves
`ConditionSet` when it cannot decide them. It is not a universal decision
procedure for logic or algebraic systems.

### Bound variables and result context

Formal variables in `D`, `Sum`, `Integrate`, `Solve`, `NSolve`, `DSolve`, and `Plot` shadow
same-name global values within their scope; other numeric session parameters
still apply. With `x=3`, `D[x^2,x]` returns `2*x` and `Integrate[x,x]` returns
`x**2/2`, rather than differentiating a constant or integrating the constant 3.
Use `Substitute[D[x^2,x],x,3]` to evaluate the derivative at 3. The symbolic
result can be stored through `a=D[x^2,x]` as a snapshot of `2*x`, following
the immediate assignment rules above.

Nested sum indices retain local scope. For example,
`Sum[D[n^2,n],{n,1,3}]` still returns 12; a session variable `n` does not
replace the bound index. Definitions preserve this scope distinction.

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

### Limits: development 0.2.0.dev1

This increment is in the development source; it is not included in the published
0.2.0-dev0 ZIP.

```wolfram
Limit[Sin[x]/x,x,0]
Limit[Sqrt[x^2]/x,x,0,Left]
Limit[Sqrt[x^2]/x,x,0,Right]
Limit[1/x,x,Infinity]
```

These examples yield `1`, `-1`, `1`, and `0`. `Limit[expression,variable,point]`
is **bilateral**, as is an explicit fourth argument `Both`. `Left` and `Right`
select approach through smaller or larger real values, not complex-plane
paths. They are literal options unaffected by same-named session variables.
For `Infinity` and `-Infinity`, the point determines the direction; omit the
fourth argument. Multivariate limits and complex approach points are unsupported.

Expressions may take principal-branch complex values. The approach point need
not belong to the expression domain: `Limit[(x^2-1)/(x-1),x,1]` yields `2`.
Bound-variable exclusions appear in `details.limit_expression_exclusions`;
independent exclusions remain in `conditions`. Cancelling `a*x/(a*x)`, for
example, retains `a != 0`.

Statuses distinguish `evaluated` (computed finite exact value), `unverified`
(approximate data or result without error certification), `conditional`
(hypotheses or parameter exclusions), `divergent` (infinite limit), `no_limit`
(distinct sides or oscillation), and `unresolved` (undetermined computation or
parameter branches). `Limit[1/x^2,x,0]` diverges; `Limit[1/x,x,0]` and
`Limit[Sin[1/x],x,0]` have no unique bilateral limit.

Divergent, nonexistent and unresolved limits retain an inert `Limit` with
`input=null`. They do not return scalar infinities or treat an oscillation
interval as a limit value. Inspect `details.sides`, `details.extended_value`
when present, and warnings. `exact=true` describes a representation without
Float; it does not prove existence or certify the limit. `verification` stays
`not_checked`: no independent epsilon-delta proof is provided.

The variable is local even when assigned in the session. Hypotheses involving
it must hold throughout a full one-sided neighbourhood, apart from the point.
`Assuming[x>0,Limit[Sqrt[x^2]/x,x,0,Right]]` is accepted; requesting a bilateral
limit with that hypothesis is rejected. Discrete, mixed or unverifiable
contexts are conservatively rejected. Assigned parameter values are accepted;
branches of symbols without proven finiteness remain unresolved, even when the
backend might suggest a generic answer.

Expressions are bounded to 256 operations and eight symbols. These are
structural budgets, not effective time or memory limits. Parameter-dependent
denominator degeneracy checks are limited to rational polynomials of total
degree at most 32 and estimated expansion of at most 4096 terms; other cases
are conservatively rejected. Current JSON session
persistence cannot store inert `Limit` results; finite values within supported
types remain storable. `Series`, `Product` and other calculus extensions are
outside this increment.

The backend uses [SymPy 1.14 limits](https://docs.sympy.org/latest/modules/series/series.html#limits)
and explicitly compares both sides for `Both`.

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
The language and sessions above belong to the development code: the published
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
`Session` provides the persistent context described above; `evaluate` remains stateless.
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
