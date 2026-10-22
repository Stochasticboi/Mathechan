"""Lexical binding and local hypothesis checks for real-axis limits."""

import sympy as sp

from .domains import condition_text, require_nonzero


def _covers_approach(condition, symbol, point, direction):
    """Prove a full punctured one-sided neighbourhood is allowed, or decline."""
    condition = condition.replace(
        lambda item: isinstance(item, sp.Contains) and item.args[0] == symbol
        and item.args[1] in (sp.S.Reals, sp.S.Complexes),
        lambda item: sp.true,
    ).replace(
        lambda item: isinstance(item, sp.Contains) and isinstance(item.args[1], sp.Interval),
        lambda item: item.args[1].as_relational(item.args[0]),
    )
    if condition is sp.true:
        return True
    if condition.free_symbols - {symbol} or sp.count_ops(condition) > 64:
        return False
    try:
        permitted = condition.as_set()
        if permitted == sp.S.Reals:
            return True
        intervals = permitted.args if isinstance(permitted, sp.Union) else (permitted,)
        sides = ("Left", "Right") if direction == "Both" else (direction,)
        if point == sp.oo:
            return any(isinstance(i, sp.Interval) and i.end == sp.oo for i in intervals)
        if point == -sp.oo:
            return any(isinstance(i, sp.Interval) and i.start == -sp.oo for i in intervals)
        for side in sides:
            if not any(isinstance(i, sp.Interval) and
                       (sp.And(i.start < point, i.end >= point) if side == "Left"
                        else sp.And(i.start <= point, i.end > point)) is sp.true
                       for i in intervals):
                return False
        return True
    except (ValueError, TypeError, NotImplementedError):
        return False


def evaluate_limit(node, build, restrictions, state, bindings, functions, definitions):
    from .language_ops import EvaluationState, arity, scalar, variable
    from .limits import limit_expression

    arity(node, 3, 4)
    symbol = variable(node.children[1])
    direction = "Both"
    if len(node.children) == 4:
        option = node.children[3]
        if option.kind != "name" or option.value not in ("Both", "Left", "Right"):
            raise ValueError("Limit admite la dirección Both, Left o Right.")
        direction = option.value
    point = scalar(build(node.children[2], restrictions, state, bindings, functions, definitions))
    scope = {name: value for name, value in bindings.items() if name != str(symbol)}
    local_definitions = {name: value for name, value in definitions.items() if name != str(symbol)}
    local = []
    child = EvaluationState(sum_terms=state.sum_terms, assumptions=state.assumptions,
                            call_depth=state.call_depth, steps=state.steps)
    expression = scalar(build(node.children[0], local, child, scope, functions, local_definitions))
    state.sum_terms, state.steps = child.sum_terms, child.steps
    for combined in (child.assumptions, *child.requirements):
        for condition in sp.And.make_args(combined):
            if symbol in condition.free_symbols and not _covers_approach(condition, symbol, point, direction):
                raise ValueError("No se pueden verificar las hipótesis en el entorno lateral solicitado por Limit.")
    outcome = limit_expression(expression, symbol, point, direction)
    state.absorb(outcome)
    state.mark_status(child.status)
    state.warnings.extend(child.warnings)
    free_restrictions = [item for item in local if symbol not in item.free_symbols]
    for item in local:
        if symbol in item.free_symbols:
            if sp.count_ops(item) > 256 or len(item.free_symbols) > 8:
                raise ValueError("La exclusión de Limit excede 256 operaciones u ocho símbolos.")
            independent, dependent = sp.factor_terms(item).as_independent(symbol, as_Add=False)
            require_nonzero(independent, free_restrictions)
            if dependent.free_symbols - {symbol}:
                if not dependent.is_polynomial(symbol):
                    raise ValueError("No se puede verificar el dominio local del denominador paramétrico de Limit.")
                from .algebra import _rational_shape
                _, degree, _, _ = _rational_shape(dependent)
                if degree > 32:
                    raise ValueError("La verificación del denominador paramétrico de Limit admite grado hasta 32.")
                coefficients = sp.Poly(dependent, symbol).all_coeffs()
                nontrivial = sp.Or(*(sp.Ne(coefficient, 0) for coefficient in coefficients))
                if nontrivial is sp.false:
                    raise ValueError("El denominador de Limit es idénticamente nulo.")
                if nontrivial is not sp.true:
                    state.requirements.append(nontrivial)
                    state.conditions.append(sp.sstr(nontrivial))
    restrictions.extend(free_restrictions)
    bound_restrictions = [item for item in local if symbol in item.free_symbols]
    for condition in child.requirements:
        if symbol not in condition.free_symbols:
            state.requirements.append(condition)
            state.conditions.append(sp.sstr(condition))
            state.mark_status("conditional")
    if bound_restrictions:
        state.details["limit_expression_exclusions"] = list(condition_text(bound_restrictions))
        state.warnings.append("Las exclusiones de la variable ligada pertenecen a la expresión original; no se exige definirla en el punto límite.")
    if child.conditions or child.details:
        state.details["limit_expression_context"] = {
            "conditions": list(child.conditions), "details": child.details,
        }
    if free_restrictions or state.requirements:
        state.mark_status("conditional")
    return outcome.value
