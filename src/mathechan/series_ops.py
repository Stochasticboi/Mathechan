"""Bounded univariate local expansions preserving SymPy's Order remainder.

Orders describe local asymptotic remainders, never a global numerical error bound.
The expansion follows a real one-sided path, including for complex-valued input.
"""

import sympy as sp
from sympy.core.function import PoleError

from .calculus import OperationOutcome


def series_parameter_exclusions(expr, variable, point):
    """Find generic branch degeneracies even when hidden in the Order term.

    A fractional/negative power or logarithm with parameter-dependent center
    can cease to be regular when its base vanishes. At infinity, a vanishing
    leading coefficient changes the dominant balance. These exclusions are
    deliberately conservative; the degenerate case needs its own expansion.
    """
    exclusions = []
    for node in sp.preorder_traversal(expr):
        base = None
        if isinstance(node, sp.Pow) and (node.exp.is_integer is not True or node.exp.is_negative is True):
            base = node.base
        elif node.func is sp.log:
            base = node.args[0]
        if base is None or not base.has(variable):
            continue
        if point not in (sp.oo, -sp.oo):
            candidates = (base.subs(variable, point),)
        else:
            numerator, denominator = sp.fraction(base)
            candidates = []
            for part in (numerator, denominator):
                if part.is_polynomial(variable):
                    candidates.append(sp.Poly(part, variable).LC())
        for candidate in candidates:
            if (candidate.free_symbols and not candidate.has(variable, sp.nan, sp.zoo, sp.oo, -sp.oo)
                    and candidate.is_zero is None and candidate not in exclusions):
                exclusions.append(candidate)
    return tuple(exclusions)


def series_expression(expr, variable, point, order, direction="Right"):
    """Expand below ``order``; keep failures inert and parameter exclusions explicit."""
    if not isinstance(variable, sp.Symbol):
        raise ValueError("La variable de Series debe ser un símbolo.")
    if not isinstance(expr, sp.Expr) or expr.has(sp.nan, sp.zoo, sp.oo, -sp.oo):
        raise ValueError("Series requiere una expresión simbólica finita.")
    if (
        not isinstance(point, sp.Expr)
        or point.has(variable, sp.nan, sp.zoo)
        or point.is_extended_real is not True
    ):
        raise ValueError("El punto debe ser real e independiente de la variable; se admiten infinitos reales.")
    if isinstance(order, bool) or not isinstance(order, (int, sp.Integer)) or not 1 <= order <= 32:
        raise ValueError("El orden de Series debe ser un entero entre 1 y 32.")
    if direction not in ("Left", "Right"):
        raise ValueError("La dirección de Series debe ser Left o Right.")
    if sp.count_ops(expr) > 256 or len(expr.free_symbols | point.free_symbols) > 8:
        raise ValueError("Series admite hasta 256 operaciones y ocho símbolos.")
    order = int(order)
    path = "Left" if point == sp.oo else "Right" if point == -sp.oo else direction
    details = {
        "method": "sympy.series", "sympy_version": sp.__version__,
        "variable": sp.sstr(variable), "point": sp.sstr(point),
        "order": order, "direction": path, "path": "real",
        "global_equality": False, "certified_numeric_error": False,
        "convergence_radius": "not_determined",
    }
    inert = sp.Function("Series")(expr, variable, point, sp.Integer(order), sp.Symbol(path))
    try:
        result = sp.series(expr, variable, point, order, dir="-" if path == "Left" else "+")
    except (NotImplementedError, ValueError, TypeError, PoleError, RecursionError, OverflowError):
        return OperationOutcome(
            inert, "unresolved", warnings=("El backend no determinó una expansión dentro del alcance admitido.",),
            details=details,
        )
    if not isinstance(result, sp.Expr) or result.removeO().has(sp.nan, sp.zoo, sp.oo, -sp.oo):
        return OperationOutcome(inert, "unresolved", details=details)
    remainders = sorted(result.atoms(sp.Order), key=sp.default_sort_key)
    if not remainders and not result.is_polynomial(variable):
        # Accept exact finite Laurent/Puiseux sums, but not an unchanged essential
        # singularity such as exp(1/x), which the backend may return verbatim.
        shifted = result.subs(variable, variable + point) if point not in (sp.oo, -sp.oo) else result
        terms = sp.Add.make_args(sp.expand(shifted))
        finite_power_sum = all(
            term.as_coeff_exponent(variable)[1].is_Rational
            and not term.as_coeff_exponent(variable)[0].has(variable)
            for term in terms
        )
        if not finite_power_sum:
            return OperationOutcome(inert, "unresolved", warnings=("No se obtuvo una expansión truncada verificable.",), details=details)
    conditions = []
    parameter_exclusions = series_parameter_exclusions(expr, variable, point)
    for exclusion in parameter_exclusions:
        conditions.append(f"Rama genérica: {sp.sstr(sp.Ne(exclusion, 0))}")
    parameters = (expr.free_symbols | point.free_symbols) - {variable}
    for parameter in sorted(parameters, key=sp.default_sort_key):
        if parameter.is_finite is not True:
            conditions.append(f"Parámetro finito: {sp.sstr(sp.Contains(parameter, sp.S.Complexes))}")
    # Coefficient poles signal degenerate parameter cases excluded from this
    # branch. They are conditions, never silently assumed nonzero.
    polynomial_part = result.removeO() if remainders else result
    for term in sp.Add.make_args(polynomial_part):
        denominator = sp.denom(term)
        for factor in sp.Mul.make_args(denominator):
            base = factor.base if isinstance(factor, sp.Pow) else factor
            if base.free_symbols and not base.has(variable) and base.is_zero is not False:
                condition = f"Coeficiente definido: {sp.sstr(sp.Ne(base, 0))}"
                if condition not in conditions:
                    conditions.append(condition)
    for node in sp.preorder_traversal(polynomial_part):
        base = None
        if isinstance(node, sp.Pow) and (node.exp.is_integer is not True or node.exp.is_negative is True):
            base = node.base
        elif node.func is sp.log:
            base = node.args[0]
        if base is not None and base.free_symbols and not base.has(variable) and base.is_zero is not False:
            condition = f"Coeficiente definido: {sp.sstr(sp.Ne(base, 0))}"
            if condition not in conditions:
                conditions.append(condition)
    if result.has(sp.Derivative):
        conditions.append("La expansión formal requiere la regularidad local de las funciones no especificadas.")
    warnings = []
    if remainders:
        warnings.append("O conserva el orden del resto local; no es una cota numérica ni una igualdad global.")
    if conditions:
        warnings.append("Los casos degenerados de parámetros no quedan resueltos por esta rama.")
    # An exact finite expression on a lateral branch need not equal the input
    # elsewhere: Abs(x) -> x on the right, or Abs(x-1) -> 1-x near zero.
    # Absence of Order alone therefore never establishes global equality.
    global_equality = not remainders and result == expr
    local_identity_only = not remainders and not global_equality
    if local_identity_only:
        conditions.append("La igualdad solo se establece en el entorno lateral de la expansión; no se determinó su extensión global.")
        warnings.append("La expresión sin O sigue siendo una identidad local de rama, no una igualdad global.")
    details.update(
        remainder=[sp.sstr(item) for item in remainders],
        truncated=bool(remainders), global_equality=global_equality,
        local_identity_only=local_identity_only,
        parameter_branches_complete=not conditions,
    )
    status = "series" if remainders else "conditional" if local_identity_only else "evaluated"
    return OperationOutcome(result, status, tuple(conditions), tuple(warnings), details)
