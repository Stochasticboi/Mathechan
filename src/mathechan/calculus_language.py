"""Scoped language bindings for differential calculus, series and aggregates."""

from dataclasses import replace

import sympy as sp

from .domains import condition_text, require_nonzero, parameter_domain_conditions


CALLS = frozenset({"D", "Series", "Normal", "Sum", "Product", "Grad", "Div", "Curl", "Jacobian", "Hessian"})


def calculus_call(node, build, restrictions, state, bindings, functions, definitions):
    from .language_ops import EvaluationState, arity, checked_restrictions, scalar, variable
    from .differential_ops import derivative_expression, vector_expression
    from .series_ops import series_expression, series_parameter_exclusions
    from .aggregation import aggregate_expression
    from .limit_language import _covers_approach

    name = node.value

    def read(child, target=restrictions, child_state=state, scope=bindings, defs=definitions):
        return build(child, target, child_state, scope, functions, defs)

    def context(symbols):
        names = {str(item) for item in symbols}
        scope = {key: value for key, value in bindings.items() if key not in names}
        defs = {key: value for key, value in definitions.items() if key not in names}
        child = EvaluationState(sum_terms=state.sum_terms, assumptions=state.assumptions,
                                call_depth=state.call_depth, steps=state.steps)
        return scope, defs, child

    def absorb_child(child):
        state.sum_terms, state.steps = child.sum_terms, child.steps
        state.mark_status(child.status)
        state.warnings.extend(child.warnings)
        state.conditions.extend(child.conditions)
        state.requirements.extend(child.requirements)
        if child.details:
            state.details.setdefault("calculus_context", []).append(child.details)

    if name == "Normal":
        arity(node, 1)
        expression = read(node.children[0])
        if not isinstance(expression, sp.Expr):
            raise ValueError("Normal requiere una expresión escalar o serie.")
        if expression.has(sp.Order):
            state.mark_status("series")
            state.warnings.append("Normal extrae una aproximación truncada; no convierte la serie en igualdad global ni certifica el error.")
            state.details["normal"] = {"removed_orders": [sp.sstr(item) for item in expression.atoms(sp.Order)],
                                       "global_equality": False}
            return expression.removeO()
        return expression

    if name == "D":
        if not 2 <= len(node.children) <= 9:
            raise ValueError("D requiere una expresión y hasta ocho especificaciones de derivación.")
        specs = []
        for item in node.children[1:]:
            if item.kind == "list":
                if len(item.children) != 2:
                    raise ValueError("Use D[expr,{variable,orden}] o especificaciones sucesivas.")
                specs.append((variable(item.children[0]), read(item.children[1])))
            else:
                specs.append((variable(item), sp.S.One))
        symbols = [item[0] for item in specs]
        scope, defs, child = context(symbols)
        local = []
        expression = scalar(read(node.children[0], local, child, scope, defs))
        outcome = derivative_expression(expression, specs)
        absorb_child(child)
        if functions and outcome.value.has(sp.Derivative):
            # A formal derivative inside DSolve is its equation's input,
            # not a failed attempt to solve that equation.
            state.details.update(outcome.details)
        else:
            state.absorb(outcome)
        mapping = {sp.Symbol(key): value for key, value in bindings.items()}
        restrictions.extend(checked_restrictions([item.subs(mapping, simultaneous=True) for item in local]))
        return outcome.value.subs(mapping, simultaneous=True)

    if name in ("Grad", "Div", "Curl", "Jacobian", "Hessian"):
        arity(node, 2, 3, 4) if name == "Jacobian" else arity(node, 2, 3)
        spec = node.children[1]
        if spec.kind != "list":
            raise ValueError("El cálculo vectorial requiere una lista de variables.")
        symbols = tuple(variable(item) for item in spec.children)
        chart, mode = "Cartesian", "Components"
        if len(node.children) >= 3:
            option = node.children[2]
            if option.kind not in ("name", "string") or option.value not in ("Cartesian", "Cylindrical", "Spherical"):
                raise ValueError("El sistema debe ser Cartesian, Cylindrical o Spherical.")
            chart = option.value
        if len(node.children) == 4:
            option = node.children[3]
            if option.kind not in ("name", "string") or option.value not in ("Components", "Orthonormal"):
                raise ValueError("Jacobian admite Components u Orthonormal como modo.")
            mode = option.value
        scope, defs, child = context(symbols)
        chart_requirements = ()
        if chart != "Cartesian":
            from .coordinate_calculus import chart_conditions
            from .assumptions import combine_assumptions
            chart_requirements = chart_conditions(symbols, chart)
            child.assumptions = combine_assumptions(child.assumptions, sp.And(*chart_requirements))
        local = []
        expression = read(node.children[0], local, child, scope, defs)
        outcome = vector_expression(name, expression, symbols, chart, mode)
        mapping = {sp.Symbol(key): value for key, value in bindings.items()}
        requirements = []
        for condition in (*sp.And.make_args(child.assumptions), *child.requirements, *chart_requirements):
            condition = sp.simplify(condition.subs(mapping, simultaneous=True))
            if condition is sp.false:
                raise ValueError("El punto de evaluación viola las condiciones de la carta o del campo.")
            if condition is not sp.true and condition not in requirements:
                requirements.append(condition)
        child.requirements = requirements
        child.conditions = [sp.sstr(condition) for condition in requirements]
        local = checked_restrictions([item.subs(mapping, simultaneous=True) for item in local])
        details = dict(outcome.details)
        if chart_requirements:
            details["chart_requirements"] = [sp.sstr(condition) for condition in
                (sp.simplify(item.subs(mapping, simultaneous=True)) for item in chart_requirements)
                if condition is not sp.true]
        if any(symbol in mapping and mapping[symbol] != symbol for symbol in symbols):
            details["coordinate_values"] = [sp.sstr(symbol.subs(mapping, simultaneous=True)) for symbol in symbols]
        outcome = replace(outcome, value=outcome.value.subs(mapping, simultaneous=True), details=details,
                          conditions=tuple(map(sp.sstr, requirements)),
                          status="evaluated" if outcome.status == "conditional" and not requirements else outcome.status)
        absorb_child(child)
        state.absorb(outcome)
        if requirements:
            state.mark_status("conditional")
        restrictions.extend(local)
        return outcome.value

    if name == "Series":
        arity(node, 2, 3)
        spec = node.children[1]
        if spec.kind != "list" or len(spec.children) != 3:
            raise ValueError("Use Series[expresión,{variable,punto,orden}] con orden de Taylor entre 0 y 31.")
        symbol = variable(spec.children[0])
        point, order = (scalar(read(item)) for item in spec.children[1:])
        if not isinstance(order, sp.Integer) or not 0 <= order <= 31:
            raise ValueError("El orden de Taylor debe ser un entero entre 0 y 31.")
        direction = "Right"
        if len(node.children) == 3:
            option = node.children[2]
            if option.kind != "name" or option.value not in ("Right", "Left"):
                raise ValueError("Series admite Right o Left como dirección.")
            direction = option.value
        scope, defs, child = context((symbol,))
        local = []
        expression = scalar(read(node.children[0], local, child, scope, defs))
        for combined in (child.assumptions, *child.requirements):
            for condition in sp.And.make_args(combined):
                if symbol in condition.free_symbols and not _covers_approach(condition, symbol, point, direction):
                    raise ValueError("No se verifican las hipótesis en el entorno de la serie.")
        # Wolfram's n includes the degree-n term; SymPy uses the first omitted order.
        outcome = series_expression(expression, symbol, point, order + 1, direction)
        state.absorb(outcome)
        state.steps, state.sum_terms = child.steps, child.sum_terms
        state.warnings.extend(child.warnings)
        state.details["requested_taylor_degree"] = int(order)
        for base in series_parameter_exclusions(expression, symbol, point):
            require_nonzero(base, restrictions)
        parameters = expression.free_symbols - {symbol}
        for parameter in parameters:
            condition = sp.Contains(parameter, sp.S.Complexes)
            if condition is not sp.true:
                state.requirements.append(condition)
                state.conditions.append(sp.sstr(condition))
        free, requirements = parameter_domain_conditions(local, (symbol,))
        restrictions.extend(free)
        state.requirements.extend(requirements)
        state.conditions.extend(sp.sstr(condition) for condition in requirements)
        if local:
            state.details["series_original_exclusions"] = list(condition_text(local))
        # Coefficients of a local branch must remain defined after later substitution.
        polynomial = outcome.value.removeO()
        for term in sp.preorder_traversal(polynomial):
            base = None
            if isinstance(term, sp.Pow) and (term.exp.is_negative is True or term.exp.is_integer is not True):
                base = term.base
            elif term.func == sp.log:
                base = term.args[0]
            if base is not None and base.free_symbols and not base.has(symbol):
                require_nonzero(base, restrictions)
        for condition in child.requirements:
            if symbol not in condition.free_symbols:
                state.requirements.append(condition)
                state.conditions.append(sp.sstr(condition))
        if outcome.value.has(sp.Order):
            state.mark_status("series")
        elif outcome.details.get("local_identity_only"):
            state.mark_status("series")
            state.warnings.append("Esta aproximación truncada sólo representa la rama local; no tiene validez global certificada.")
        elif state.requirements or restrictions:
            state.mark_status("conditional")
        return outcome.value

    if name in ("Sum", "Product"):
        if not 2 <= len(node.children) <= 4:
            raise ValueError("Sum y Product requieren entre uno y tres rangos {índice,mínimo,máximo}.")
        raw_ranges = node.children[1:]
        if any(item.kind != "list" or len(item.children) != 3 for item in raw_ranges):
            raise ValueError("Cada rango requiere {índice,mínimo,máximo}.")
        symbols = tuple(variable(item.children[0]) for item in raw_ranges)
        if len(set(symbols)) != len(symbols):
            raise ValueError("Los índices deben ser distintos.")
        scope, defs, child = context(symbols)
        identity = sp.S.Zero if name == "Sum" else sp.S.One
        constructor = sp.Add if name == "Sum" else sp.Mul
        local = []

        class SymbolicRange(Exception):
            pass

        def finite(position, current):
            if position == len(raw_ranges):
                conditions = []
                value = scalar(read(node.children[0], conditions, child, current, defs))
                restrictions_here = checked_restrictions(conditions)
                local.extend(restrictions_here)
                mapping = {sp.Symbol(key): value for key, value in current.items()}
                for requirement in (child.assumptions, *child.requirements):
                    sampled = sp.simplify(requirement.subs(mapping, simultaneous=True))
                    if sampled is sp.false:
                        raise ValueError("Un término viola las hipótesis del agregado.")
                return value
            raw = raw_ranges[position]
            lower, upper = (scalar(read(item, local, child, {**bindings, **current}, definitions))
                            for item in raw.children[1:])
            if not isinstance(lower, sp.Integer) or not isinstance(upper, sp.Integer):
                raise SymbolicRange
            count = max(0, int(upper - lower + 1))
            if count > 1000 or child.sum_terms + count > 2000:
                raise ValueError("Presupuesto excedido: 1000 términos por rango y 2000 en total.")
            child.sum_terms += count
            return constructor(*(finite(position + 1, {**current, str(symbols[position]): sp.Integer(index)})
                                 for index in range(int(lower), int(upper) + 1))) if count else identity

        try:
            result = finite(0, scope)
        except SymbolicRange:
            scope, defs, child = context(symbols)
            local = []
            ranges = tuple((symbol, *(scalar(read(item, local, child,
                                {**bindings, **{str(s): s for s in symbols[:position]}}, definitions))
                                      for item in raw.children[1:]))
                           for position, (symbol, raw) in enumerate(zip(symbols, raw_ranges)))
            expression = scalar(read(node.children[0], local, child, scope, defs))
            constructor_held = sp.Sum if name == "Sum" else sp.Product
            for exclusion in local:
                involved = exclusion.free_symbols & set(symbols)
                if not involved:
                    restrictions.append(exclusion)
                    continue
                constant, dependent = sp.factor_terms(exclusion).as_independent(*symbols, as_Add=False)
                require_nonzero(constant, restrictions)
                valid = False
                if len(symbols) == 1:
                    symbol, lower, upper = ranges[0]
                    try:
                        zeros = sp.solveset(dependent, symbol, domain=sp.S.Reals)
                        allowed = sp.Intersection(sp.Interval(lower, upper), sp.S.Integers)
                        valid = sp.Intersection(zeros, allowed).is_empty is True
                    except (ValueError, TypeError, NotImplementedError):
                        pass
                if not valid:
                    state.mark_status("unresolved")
                    state.details["aggregate_exclusions"] = list(condition_text(local))
                    state.warnings.append("No se pudo verificar el dominio del término en todo el rango simbólico.")
                    return constructor_held(expression, *reversed(ranges))
            for combined in (child.assumptions, *child.requirements):
                for condition in sp.And.make_args(combined):
                    if condition.free_symbols & set(symbols):
                        valid = False
                        if len(symbols) == 1 and not (condition.free_symbols - set(symbols)):
                            try:
                                permitted = condition.as_set()
                                allowed = sp.Intersection(sp.Interval(ranges[0][1], ranges[0][2]), sp.S.Integers)
                                valid = allowed.is_subset(permitted) is True
                            except (ValueError, TypeError, NotImplementedError):
                                pass
                        if not valid:
                            raise ValueError("No se pudieron verificar las hipótesis del agregado simbólico.")
            outcome = aggregate_expression(expression, ranges, name)
            cost = outcome.details.get("expanded_terms", 0)
            if child.sum_terms + cost > 2000:
                raise ValueError("El agregado excede 2000 términos compartidos.")
            child.sum_terms += cost
            state.absorb(outcome)
            # Conditions on finite symbolic bounds are real integer requirements,
            # not just strings that disappear on substitution.
            for _, lower, upper in ranges:
                for bound in (lower, upper):
                    if (bound not in (sp.oo, -sp.oo) and bound.is_integer is None
                            and not bound.free_symbols & set(symbols)):
                        state.requirements.append(sp.Contains(bound, sp.S.Integers))
            result = outcome.value
            if result.has(sp.Piecewise):
                state.mark_status("conditional")
            state.steps, state.sum_terms = child.steps, child.sum_terms
            state.warnings.extend(child.warnings)
            for condition in child.requirements:
                if not condition.free_symbols & set(symbols):
                    state.requirements.append(condition)
                    state.conditions.append(sp.sstr(condition))
            return result
        absorb_child(child)
        restrictions.extend(checked_restrictions(local))
        return result
    raise ValueError("Operación de cálculo no admitida.")
