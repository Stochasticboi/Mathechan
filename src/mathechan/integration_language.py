"""Iterated symbolic integrals retaining bound scope and parameter exclusions."""

import sympy as sp

from .domains import condition_text, parameter_domain_conditions


def integration_call(node, build, restrictions, state, bindings, functions, definitions):
    from .calculus import integrate_expression
    from .language_ops import EvaluationState, scalar, variable, REAL_BOUNDS, _check_integral_hypotheses
    from .assumptions import predicates
    from sympy.calculus.util import continuous_domain, function_range

    if not 2 <= len(node.children) <= 4:
        raise ValueError("Integrate admite de una a tres variables o rangos.")
    specs = node.children[1:]
    symbols = []
    for spec in specs:
        if spec.kind == "list":
            if len(spec.children) != 3:
                raise ValueError("Integrate requiere {variable,mínimo,máximo}.")
            symbols.append(variable(spec.children[0]))
        else:
            symbols.append(variable(spec))
    if len(set(symbols)) != len(symbols):
        raise ValueError("Las variables de una integral iterada deben ser distintas; anide las antiderivadas repetidas.")
    names = {str(symbol) for symbol in symbols}
    scope = {name: value for name, value in bindings.items() if name not in names}
    defs = {name: value for name, value in definitions.items() if name not in names}
    child = EvaluationState(sum_terms=state.sum_terms, assumptions=state.assumptions,
                            call_depth=state.call_depth, steps=state.steps)
    local = []
    endpoint_exclusions = []

    def read(item, bound=False, position=0):
        endpoint_scope = {**bindings, **{str(s): s for s in symbols[:position]}}
        return build(item, endpoint_exclusions if bound else local, child,
                     endpoint_scope if bound else scope, functions, definitions if bound else defs)

    expression = scalar(read(node.children[0]))
    if sp.count_ops(expression) > 256 or len(expression.free_symbols) > 8:
        raise ValueError("Integrate admite 256 operaciones y ocho símbolos.")
    ranges = []
    for position, (symbol, spec) in enumerate(zip(symbols, specs)):
        bounds = tuple(scalar(read(item, True, position)) for item in spec.children[1:]) if spec.kind == "list" else None
        if bounds:
            if any(bound.free_symbols & set(symbols[position:]) for bound in bounds):
                raise ValueError("Los límites solo pueden depender de variables exteriores.")
            _check_integral_hypotheses(symbol, bounds, child)
            for bound in bounds:
                dependent = bound.free_symbols & set(symbols[:position])
                if dependent:
                    real_aliases = {s: sp.Dummy(str(s), real=True) for s in symbols[:position]}
                    for parameter in bound.free_symbols - set(symbols):
                        if sp.ask(sp.Q.real(parameter), predicates(child.assumptions)) is not True:
                            raise ValueError("No se pudo verificar que el límite dependiente sea real en todo el rango exterior.")
                        real_aliases[parameter] = sp.Dummy(str(parameter), real=True)
                    candidate = bound.xreplace(real_aliases)
                    for outer, outer_bounds in ranges:
                        if outer not in dependent:
                            continue
                        if outer_bounds is None:
                            raise ValueError("Un límite dependiente requiere un rango exterior real explícito.")
                        interval = sp.Interval(sp.Min(*outer_bounds), sp.Max(*outer_bounds)).xreplace(real_aliases)
                        alias = real_aliases[outer]
                        try:
                            domain = continuous_domain(candidate, alias, sp.S.Reals)
                            valid = interval.is_subset(domain) is True
                            if valid and candidate.is_real is not True:
                                image = function_range(candidate, alias, interval)
                                valid = image.is_subset(sp.S.Reals) is True
                        except (ValueError, TypeError, NotImplementedError):
                            valid = False
                        if not valid:
                            raise ValueError("El límite interior no es real y finito en todo el rango exterior, o no se pudo comprobar.")
        ranges.append((symbol, bounds))
    free, requirements = parameter_domain_conditions(local + endpoint_exclusions, tuple(symbols))
    restrictions.extend(free)
    state.requirements.extend(requirements)
    state.conditions.extend(sp.sstr(item) for item in requirements)
    state.steps, state.sum_terms = child.steps, child.sum_terms
    state.mark_status(child.status)
    state.warnings.extend(child.warnings)
    state.requirements.extend(child.requirements)
    state.conditions.extend(child.conditions)
    outcomes = []
    for symbol, bounds in reversed(ranges):
        if expression.has(sp.Integral):
            expression = sp.Integral(expression, (symbol, *bounds) if bounds else symbol)
            state.mark_status("unresolved")
            continue
        outcome = integrate_expression(expression, symbol, bounds)
        state.absorb(outcome)
        # Realness of dependent endpoints has just been checked on the outer
        # ranges; do not export their bound variables as free requirements.
        state.conditions[:] = [condition for condition in state.conditions
                               if not any(condition == f"Límite real: {sp.sstr(sp.Contains(bound, sp.S.Reals))}"
                                          for bound in bounds or () if bound.free_symbols & set(symbols))]
        expression = outcome.value
        outcomes.append(outcome.details)
        if bounds:
            for bound in bounds:
                if bound.is_extended_real is None and not bound.free_symbols & set(symbols):
                    state.requirements.append(sp.Contains(bound, REAL_BOUNDS))
                    state.mark_status("conditional")
    bound_conditions = [item for item in local + endpoint_exclusions if item.free_symbols & set(symbols)]
    if bound_conditions:
        state.details["integrand_conditions"] = list(condition_text(bound_conditions))
        state.warnings.append("Las exclusiones del integrando en su variable ligada no son condiciones libres del resultado.")
    if len(ranges) > 1:
        state.details["iterated_integration"] = {"order": "outermost_first", "variables": list(map(str, symbols)),
                                                  "steps": outcomes, "fubini_conditions": "not_certified"}
    return expression.subs({sp.Symbol(name): value for name, value in bindings.items()}, simultaneous=True)
