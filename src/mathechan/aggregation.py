"""Bounded integer aggregates with empty-range and convergence safeguards."""

import sympy as sp

from .calculus import OperationOutcome


def aggregate_expression(expr, ranges, operation="Sum"):
    """Evaluate iterated aggregates; the first range is the outermost.

    Unlike SymPy's Karr convention, a finite reversed range is empty. Symbolic
    finite bounds require integer conditions and preserve the empty branch.
    Infinite aggregates never expose an unverified scalar as a convergent value.
    Structural budgets do not constitute a wall-clock timeout.
    """
    if operation not in ("Sum", "Product"):
        raise ValueError("La operación debe ser Sum o Product.")
    if not isinstance(expr, sp.Expr) or expr.has(sp.nan, sp.zoo, sp.oo, -sp.oo):
        raise ValueError("Se requiere una expresión escalar finita.")
    if not isinstance(ranges, (tuple, list)) or not 1 <= len(ranges) <= 3:
        raise ValueError("Se requieren entre uno y tres rangos.")
    normalized, indices, conditions = [], [], []
    pending_bound_integrality = False
    symbols = set(expr.free_symbols)
    for item in ranges:
        if not isinstance(item, (tuple, list, sp.Tuple)) or len(item) != 3:
            raise ValueError("Cada rango debe tener índice, mínimo y máximo.")
        variable, lower, upper = item
        if not isinstance(variable, sp.Symbol) or variable in indices:
            raise ValueError("Los índices deben ser símbolos distintos.")
        lower = sp.Integer(lower) if isinstance(lower, int) and not isinstance(lower, bool) else lower
        upper = sp.Integer(upper) if isinstance(upper, int) and not isinstance(upper, bool) else upper
        for bound in (lower, upper):
            if not isinstance(bound, sp.Expr) or bound.has(variable, sp.nan, sp.zoo):
                raise ValueError("Los límites deben ser independientes de su índice.")
            if bound not in (sp.oo, -sp.oo):
                # Outer iterator symbols denote integers only inside this
                # aggregate. Test in a temporary integer scope, never attach
                # assumptions to the user's symbols or export a bound index.
                scoped_bound = bound.xreplace({index: sp.Dummy(integer=True) for index in indices})
                if scoped_bound.is_integer is False or bound.has(sp.Float):
                    raise ValueError("Los límites finitos deben ser enteros.")
                if scoped_bound.is_integer is None:
                    if bound.free_symbols & set(indices):
                        pending_bound_integrality = True
                    else:
                        conditions.append(sp.sstr(sp.Contains(bound, sp.S.Integers)))
            symbols.update(bound.free_symbols)
        if lower == sp.oo or upper == -sp.oo:
            raise ValueError("La orientación infinita debe ir de -Infinity hacia Infinity.")
        indices.append(variable)
        normalized.append((variable, lower, upper))
    # An inner index may not occur in an outer range's bounds.
    for position, (_, lower, upper) in enumerate(normalized):
        if (lower.free_symbols | upper.free_symbols) & set(indices[position + 1:]):
            raise ValueError("Los límites solo pueden depender de índices exteriores.")
    if sp.count_ops(expr) + sum(sp.count_ops(b) for r in normalized for b in r[1:]) > 256 or len(symbols) > 8:
        raise ValueError("Se admiten hasta 256 operaciones y ocho símbolos.")
    constructor = sp.Sum if operation == "Sum" else sp.Product
    identity = sp.S.Zero if operation == "Sum" else sp.S.One
    inert = constructor(expr, *reversed(normalized))
    details = {"method": "bounded_aggregate", "sympy_version": sp.__version__,
               "operation": operation, "range_order": "outermost_first",
               "verification": "not_checked", "expanded_terms": 0}
    warnings = []
    status = "conditional" if conditions else "evaluated"
    if pending_bound_integrality:
        return OperationOutcome(
            inert, "unresolved", tuple(dict.fromkeys(conditions)),
            ("No se pudo verificar la integralidad de un límite dependiente de índices exteriores.",),
            details,
        )

    def retain(reason, divergent=False):
        nonlocal status
        status = "divergent" if divergent else "unresolved"
        warnings.append(reason)

    def evaluate_at(expression, remaining):
        nonlocal status
        if not remaining:
            return expression
        variable, lower, upper = remaining[0]
        if (lower - upper).is_positive is True:
            return identity
        if isinstance(lower, sp.Integer) and isinstance(upper, sp.Integer):
            count = max(0, int(upper - lower + 1))
            if count > 1000 or details["expanded_terms"] + count > 2000:
                raise ValueError("Presupuesto excedido: 1000 términos por rango y 2000 en total.")
            details["expanded_terms"] += count
            values = []
            for index in range(int(lower), int(upper) + 1):
                replacement = {variable: sp.Integer(index)}
                nested = tuple((v, a.xreplace(replacement), b.xreplace(replacement))
                               for v, a, b in remaining[1:])
                values.append(evaluate_at(expression.xreplace(replacement), nested))
            return sp.Add(*values) if operation == "Sum" else sp.Mul(*values)
        inner = evaluate_at(expression, remaining[1:])
        request = constructor(inner, (variable, lower, upper))
        infinite = lower == -sp.oo or upper == sp.oo
        if infinite and inner.has(sp.Sum, sp.Product):
            retain("No se resolvió la convergencia del agregado interior.")
            return request
        try:
            result = request.doit(deep=False)
        except (NotImplementedError, ValueError, TypeError, RecursionError):
            retain("El método no determinó el agregado solicitado.")
            return request
        if not infinite:
            if result.has(sp.Sum, sp.Product):
                retain("El agregado simbólico permanece pendiente.")
            if (lower <= upper) is not sp.S.true:
                if status == "evaluated":
                    status = "conditional"
                result = sp.Piecewise((identity, lower > upper), (result, True))
            return result
        if isinstance(result, sp.Piecewise):
            branches = []
            for value, condition in result.args:
                if value.has(sp.Sum, sp.Product, sp.oo, -sp.oo, sp.nan, sp.zoo, sp.AccumBounds):
                    value = request
                branches.append((value, condition))
            if any(value != request for value, _ in branches):
                status = "conditional" if status not in ("unresolved", "divergent") else status
                warnings.append("Las condiciones de convergencia son alternativas de Piecewise.")
                return sp.Piecewise(*branches)
        try:
            convergent = request.is_convergent()
        except (NotImplementedError, ValueError, TypeError, RecursionError):
            convergent = None
        if convergent is sp.S.false or convergent is False:
            retain("El agregado infinito no converge a un valor finito admitido.", divergent=True)
            return request
        if convergent is not sp.S.true and convergent is not True:
            retain("No se pudo demostrar la convergencia; se conserva el agregado.")
            return request
        if result.has(sp.Sum, sp.Product, sp.oo, -sp.oo, sp.nan, sp.zoo, sp.AccumBounds):
            retain("La convergencia se reconoce, pero el valor permanece pendiente.")
            return request
        return result

    value = evaluate_at(expr, tuple(normalized))
    # Infinity in an inert aggregate's bounds is not a divergent scalar value.
    scalar_view = value.xreplace({item: sp.Dummy("pending")
                                 for item in value.atoms(sp.Sum, sp.Product)})
    if scalar_view.has(sp.nan, sp.zoo, sp.oo, -sp.oo, sp.AccumBounds):
        value = inert
        retain("Se detectaron términos no finitos; se conserva el agregado.")
    return OperationOutcome(value, status, tuple(dict.fromkeys(conditions)),
                            tuple(dict.fromkeys(warnings)), details)
