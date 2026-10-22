"""Bounded real-path limits with explicit bilateral comparison.

SymPy's default finite-point direction is right-sided; this module deliberately
computes both sides for ``Both``. Unbounded or indeterminate outcomes stay inert.
"""

import sympy as sp
from sympy.core.function import PoleError

from .calculus import OperationOutcome


def _kind(value):
    if value.has(sp.Limit, sp.nan, sp.zoo, sp.Piecewise):
        return "unresolved"
    if value.has(sp.AccumBounds):
        return "oscillatory"
    if value in (sp.oo, -sp.oo):
        return "infinite"
    if value.has(sp.oo, -sp.oo) or value.is_finite is not True:
        return "unresolved"
    return "finite"


def limit_expression(expr, variable, point, direction="Both"):
    """Evaluate a real univariate limit; preserve failed and divergent requests.

    The size budget is structural, not a wall-clock timeout. Parameters require
    explicit finite assumptions; unresolved parameter branches are never guessed.
    """
    if not isinstance(variable, sp.Symbol):
        raise ValueError("La variable de Limit debe ser un símbolo.")
    if not isinstance(expr, sp.Expr) or expr.has(sp.nan, sp.zoo, sp.oo, -sp.oo):
        raise ValueError("Limit requiere una expresión simbólica finita.")
    if direction not in ("Both", "Left", "Right"):
        raise ValueError("La dirección debe ser Both, Left o Right.")
    if (
        not isinstance(point, sp.Expr)
        or point.has(variable, sp.nan, sp.zoo)
        or point.is_extended_real is not True
        or (point not in (sp.oo, -sp.oo) and point.is_finite is not True)
    ):
        raise ValueError("El punto debe ser real, finito o infinito real e independiente de la variable.")
    if sp.count_ops(expr) > 256 or len(expr.free_symbols | point.free_symbols) > 8:
        raise ValueError("Limit admite hasta 256 operaciones y ocho símbolos.")
    infinite_point = point in (sp.oo, -sp.oo)
    if infinite_point and direction != "Both":
        raise ValueError("En infinito la dirección la determina el punto; omita Left o Right.")
    backend_direction = (
        "-" if point == sp.oo else "+" if point == -sp.oo else
        {"Both": "+-", "Left": "-", "Right": "+"}[direction]
    )
    inert = sp.Limit(expr, variable, point, dir=backend_direction)
    details = {
        "method": "sympy.limit", "sympy_version": sp.__version__,
        "direction": direction, "point": sp.sstr(point),
        "path": "real", "verification": "not_checked", "sides": {},
    }
    warnings = []

    def retained(status, warning):
        return OperationOutcome(inert, status, warnings=tuple(warnings + [warning]), details=details)

    parameters = (expr.free_symbols | point.free_symbols) - {variable}
    if any(parameter.is_finite is not True for parameter in parameters):
        return retained("unresolved", "No se determinaron las ramas de parámetros sin finitud explícita; se conserva Limit.")
    if expr.has(sp.Float) or point.has(sp.Float):
        warnings.append("Los datos Float tienen precisión finita; el resultado no es un límite exacto certificado.")
    requested_sides = (
        (("infinity", backend_direction),) if infinite_point else
        (("left", "-"), ("right", "+")) if direction == "Both" else
        (("left", "-"),) if direction == "Left" else (("right", "+"),)
    )
    values = []
    for side, backend_side in requested_sides:
        try:
            value = sp.limit(expr, variable, point, dir=backend_side)
        except (NotImplementedError, ValueError, TypeError, RecursionError, PoleError) as error:
            details["sides"][side] = {"status": "unresolved", "error": type(error).__name__}
            values.append((None, "unresolved"))
            continue
        kind = _kind(value)
        details["sides"][side] = {"status": kind, "value": sp.sstr(value)}
        values.append((value, kind))
    kinds = [kind for _, kind in values]
    if "unresolved" in kinds:
        return retained("unresolved", "El método no determinó todos los límites solicitados; se conserva Limit.")
    if "oscillatory" in kinds:
        return retained("no_limit", "Se detectó oscilación sin valor límite único; se conserva Limit, no un intervalo como valor.")
    first = values[0][0]
    if len(values) == 2:
        second = values[1][0]
        same = first == second
        if not same and "infinite" not in kinds:
            same = sp.simplify(first - second).is_zero
        if same is False:
            return retained("no_limit", "Los límites laterales son distintos; no existe el límite bilateral solicitado.")
        if same is not True:
            return retained("unresolved", "No se pudo determinar si coinciden ambos límites laterales; se conserva Limit.")
    if "infinite" in kinds:
        details["extended_value"] = "+oo" if first == sp.oo else "-oo"
        return retained("divergent", "El límite es infinito; no se entrega como valor escalar finito.")
    status = "unverified" if warnings or first.has(sp.Float) else "evaluated"
    if first.has(sp.Float) and not warnings:
        warnings.append("El resultado contiene aproximaciones Float; no es un límite exacto certificado.")
    return OperationOutcome(first, status, warnings=tuple(warnings), details=details)
