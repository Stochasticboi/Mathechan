"""Evaluation rules for bounded scientific operations over the existing AST."""

from dataclasses import dataclass, field

import sympy as sp

from .domains import condition_text

SCIENTIFIC_CALLS = frozenset(
    {
        "N",
        "Factor",
        "Together",
        "Cancel",
        "Substitute",
        "Sum",
        "Integrate",
        "Solve",
        "DSolve",
        "D",
    }
)
MAX_SUM_TERMS = 1000
MAX_TOTAL_SUM_TERMS = 2000
REAL_BOUNDS = sp.Union(sp.S.Reals, sp.FiniteSet(-sp.oo, sp.oo))


@dataclass
class EvaluationState:
    """Per-evaluation diagnostics and a shared finite-sum work budget."""

    status: str = "evaluated"
    warnings: list = field(default_factory=list)
    conditions: list = field(default_factory=list)
    requirements: list = field(default_factory=list)
    details: dict = field(default_factory=dict)
    sum_terms: int = 0

    def mark_status(self, status):
        priority = {
            "evaluated": 0,
            "verified": 1,
            "conditional": 2,
            "unverified": 3,
            "unresolved": 4,
            "no_solution": 5,
        }
        if priority.get(status, 0) > priority.get(self.status, 0):
            self.status = status

    def absorb(self, outcome):
        self.mark_status(outcome.status)
        self.warnings.extend(outcome.warnings)
        self.conditions.extend(outcome.conditions)
        self.details.update(outcome.details)


def variable(node):
    if node.kind != "name" or node.value in ("Pi", "E", "Infinity"):
        raise ValueError("Se requiere un símbolo como variable.")
    return sp.Symbol(node.value)


def scalar(value):
    if not isinstance(value, sp.Expr) or value.is_commutative is not True:
        raise ValueError("La operación requiere una expresión escalar.")
    return value


def arity(node, *counts):
    if len(node.children) not in counts:
        raise ValueError(f"Número de argumentos no admitido para {node.value}.")


def checked_restrictions(items):
    """Reject excluded values after binding or substitution, not after cancellation."""
    result = []
    for item in items:
        if item.is_zero is True or item.has(sp.zoo, sp.nan) or item.is_finite is False:
            raise ValueError(
                "La sustitución o el término viola el dominio original: denominador nulo o no finito."
            )
        if item.is_zero is not False and item not in result:
            result.append(item)
    return result


def substitute_bindings(value, bindings):
    return (
        value.subs(
            {sp.Symbol(name): item for name, item in bindings.items()},
            simultaneous=True,
        )
        if bindings
        else value
    )


def _filter_solutions(outcome, variables, restrictions, domain, state):
    """Apply original denominator exclusions to sets returned by equation solvers."""
    result = outcome.value
    if not restrictions or not isinstance(result, sp.Set):
        return result
    tuple_candidates = outcome.details.get("method") == "sympy.linsolve"
    if tuple_candidates and not isinstance(result, sp.FiniteSet):
        state.mark_status("conditional")
        state.warnings.append(
            "La familia de soluciones está sujeta a las exclusiones originales indicadas en conditions."
        )
        return result
    if len(variables) == 1 and not tuple_candidates:
        symbol = variables[0]
        for denominator in restrictions:
            if symbol not in denominator.free_symbols:
                if denominator.is_zero is True:
                    return sp.S.EmptySet
                if denominator.is_zero is not False:
                    state.status = (
                        "conditional" if state.status != "unresolved" else state.status
                    )
                continue
            excluded = sp.solveset(denominator, symbol, domain=domain)
            if excluded.has(sp.ConditionSet):
                state.status = "unresolved"
                state.warnings.append(
                    "No se pudieron resolver todas las exclusiones del denominador original."
                )
            result = sp.Complement(result, excluded)
    elif isinstance(result, sp.FiniteSet):
        kept = []
        for solution in result:
            mapping = dict(zip(variables, solution))
            values = [item.subs(mapping, simultaneous=True) for item in restrictions]
            if any(item.is_zero is True or item.has(sp.zoo, sp.nan) for item in values):
                continue
            if any(item.is_zero is not False for item in values):
                state.status = (
                    "conditional" if state.status != "unresolved" else state.status
                )
            kept.append(solution)
        result = sp.FiniteSet(*kept)
    return result


def _initial_domain_checks(equations, dependent, symbol, restrictions):
    """Check retained exclusions at initial points before algebra can hide them."""
    conditions = [
        item for item in equations if not item.has(sp.Derivative) or item.has(sp.Subs)
    ]
    values = {item.lhs: item.rhs for item in conditions}
    points = []
    for item in conditions:
        key = item.lhs
        if key.func == dependent.func and len(key.args) == 1:
            points.append(key.args[0])
        elif isinstance(key, sp.Subs) and len(key.point) == 1:
            points.append(key.point[0])
    unresolved = False
    for point in points:
        for restriction in restrictions:
            value = (
                restriction.subs(symbol, point).subs(values, simultaneous=True).doit()
            )
            if (
                value.is_zero is True
                or value.is_finite is False
                or value.has(sp.zoo, sp.nan)
            ):
                raise ValueError(
                    "Las condiciones iniciales están fuera del dominio original de la EDO."
                )
            unresolved = (
                unresolved or value.is_zero is not False or value.is_finite is not True
            )
    return points, unresolved


def _solution_domain_checks(outcome, points, dependent, symbol, restrictions, state):
    if not restrictions:
        return
    solutions = (
        list(outcome.value) if isinstance(outcome.value, sp.Tuple) else [outcome.value]
    )
    uncertain = False
    for solution in solutions:
        expression = (
            solution.rhs
            if isinstance(solution, sp.Equality) and solution.lhs == dependent
            else None
        )
        if expression is None:
            uncertain = True
            continue
        for point in points:
            for restriction in restrictions:
                value = (
                    restriction.subs(dependent, expression)
                    .doit()
                    .subs(symbol, point)
                    .doit()
                )
                if (
                    value.is_zero is True
                    or value.is_finite is False
                    or value.has(sp.zoo, sp.nan)
                ):
                    raise ValueError(
                        "La solución viola una exclusión del dominio original en un dato inicial."
                    )
                uncertain = (
                    uncertain
                    or value.is_zero is not False
                    or value.is_finite is not True
                )
    state.conditions.extend(
        "Dominio original de la EDO: " + item for item in condition_text(restrictions)
    )
    if state.status not in ("unresolved", "unverified"):
        state.status = "unverified" if uncertain else "conditional"
    state.details["domain_verification"] = (
        "unverified"
        if uncertain
        else "initial_points_checked"
        if points
        else "not_global"
    )
    state.warnings.append(
        "La verificación por residuos es local y está sujeta al dominio original de la EDO."
    )


def scientific_call(node, build, restrictions, state, bindings, functions, definitions=None):
    """Evaluate an admitted call; callbacks retain the parser's safety boundary."""
    from . import algebra
    from .calculus import integrate_expression, solve_equations, solve_ode

    definitions = {} if definitions is None else definitions

    def read(child, target=None, scope=None, allowed=None, child_state=None, definition_scope=None):
        return build(
            child,
            restrictions if target is None else target,
            state if child_state is None else child_state,
            bindings if scope is None else scope,
            functions if allowed is None else allowed,
            definitions if definition_scope is None else definition_scope,
        )

    def shadowed_definitions(*symbols):
        names = {str(symbol) for symbol in symbols}
        return {name: value for name, value in definitions.items() if name not in names}

    name = node.value
    if name in ("Factor", "Together", "Cancel"):
        arity(node, 1)
        operation = {
            "Factor": algebra.factor_expression,
            "Together": algebra.together_expression,
            "Cancel": algebra.cancel_expression,
        }[name]
        return operation(scalar(read(node.children[0])))
    if name == "N":
        arity(node, 1, 2)
        precision = (
            read(node.children[1]) if len(node.children) == 2 else sp.Integer(15)
        )
        value = algebra.numerical(scalar(read(node.children[0])), precision)
        state.details.setdefault("numeric_evaluations", []).append(
            {
                "requested_significant_digits": int(precision),
                "approximate": True,
            }
        )
        return value
    if name == "D":
        arity(node, 2)
        symbol = variable(node.children[1])
        scope = {key: value for key, value in bindings.items() if key != str(symbol)}
        local = []
        value = scalar(read(node.children[0], local, scope,
                            definition_scope=shadowed_definitions(symbol)))
        result = substitute_bindings(sp.diff(value, symbol), bindings)
        restrictions.extend(
            checked_restrictions(
                [substitute_bindings(item, bindings) for item in local]
            )
        )
        return result
    if name == "Substitute":
        arity(node, 3)
        symbol = variable(node.children[1])
        scope = {key: value for key, value in bindings.items() if key != str(symbol)}
        local = []
        child_state = EvaluationState(sum_terms=state.sum_terms)
        expression = scalar(
            read(node.children[0], local, scope, child_state=child_state,
                 definition_scope=shadowed_definitions(symbol))
        )
        state.sum_terms = child_state.sum_terms
        replacement = scalar(read(node.children[2]))
        result = algebra.substitute_expression(expression, symbol, replacement)
        substituted = [
            substitute_bindings(item.subs(symbol, replacement), bindings)
            for item in local
        ]
        restrictions.extend(checked_restrictions(substituted))
        for requirement in child_state.requirements:
            transformed = substitute_bindings(
                requirement.subs(symbol, replacement), bindings
            )
            if transformed is sp.S.false:
                raise ValueError(
                    "La sustitución viola una condición original del cálculo: "
                    + sp.sstr(requirement)
                )
            if transformed is not sp.S.true:
                state.requirements.append(transformed)
                state.conditions.append(
                    "Condición del cálculo: " + sp.sstr(transformed)
                )
                state.mark_status("conditional")
        if child_state.conditions or child_state.warnings or child_state.details:
            state.details.setdefault("substitution_provenance", []).append(
                {
                    "variable": str(symbol),
                    "previous_status": child_state.status,
                    "previous_conditions": list(child_state.conditions),
                    "previous_details": child_state.details,
                }
            )
        state.warnings.extend(
            item for item in child_state.warnings if "constante aditiva" in item
        )
        if result.has(sp.Integral, sp.ConditionSet):
            state.mark_status("unresolved")
            state.warnings.append(
                "El resultado sustituido conserva construcciones sin resolver."
            )
        elif result.has(sp.Piecewise):
            state.mark_status("conditional")
            for piecewise in result.atoms(sp.Piecewise):
                state.conditions.extend(
                    "Condición de rama: " + sp.sstr(condition)
                    for _, condition in piecewise.args
                    if condition is not sp.S.true
                )
        return substitute_bindings(result, bindings)
    if name == "Sum":
        arity(node, 2)
        interval = node.children[1]
        if interval.kind != "list" or len(interval.children) != 3:
            raise ValueError(
                "Sum requiere {índice, mínimo, máximo}, ambos límites enteros finitos."
            )
        symbol = variable(interval.children[0])
        lower, upper = (read(item) for item in interval.children[1:])
        if not isinstance(lower, sp.Integer) or not isinstance(upper, sp.Integer):
            raise ValueError("Sum requiere límites enteros exactos y finitos.")
        count = max(0, int(upper - lower + 1))
        if count > MAX_SUM_TERMS or state.sum_terms + count > MAX_TOTAL_SUM_TERMS:
            raise ValueError(
                "Sum excede el presupuesto: 1000 términos por suma, 2000 en total."
            )
        state.sum_terms += count
        terms = []
        for index in range(int(lower), int(upper) + 1):
            scope = dict(bindings, **{str(symbol): sp.Integer(index)})
            local = []
            terms.append(scalar(read(node.children[0], local, scope,
                                     definition_scope=shadowed_definitions(symbol))))
            restrictions.extend(checked_restrictions(local))
        return sp.Add(*terms)
    if name == "Integrate":
        arity(node, 2)
        specification = node.children[1]
        bounds = None
        if specification.kind == "list":
            if len(specification.children) != 3:
                raise ValueError("Integrate requiere {variable, mínimo, máximo}.")
            symbol = variable(specification.children[0])
            bounds = tuple(scalar(read(item)) for item in specification.children[1:])
        else:
            symbol = variable(specification)
        scope = {key: value for key, value in bindings.items() if key != str(symbol)}
        local = []
        expression = scalar(read(node.children[0], local, scope,
                                 definition_scope=shadowed_definitions(symbol)))
        outcome = integrate_expression(expression, symbol, bounds)
        state.absorb(outcome)
        if bounds:
            for bound in bounds:
                if bound.is_extended_real is None:
                    state.requirements.append(sp.Contains(bound, REAL_BOUNDS))
                    state.mark_status("conditional")
        bound_conditions = [item for item in local if symbol in item.free_symbols]
        restrictions.extend(item for item in local if symbol not in item.free_symbols)
        if bound_conditions:
            state.details.setdefault("integrand_conditions", []).extend(
                condition_text(bound_conditions)
            )
            state.warnings.append(
                "Las exclusiones del integrando en su variable ligada no son condiciones libres del resultado."
            )
        return substitute_bindings(outcome.value, bindings)
    if name == "Solve":
        arity(node, 2, 3)
        raw_variables = node.children[1]
        variables = (
            [variable(item) for item in raw_variables.children]
            if raw_variables.kind == "list"
            else [variable(raw_variables)]
        )
        if not variables or len(variables) > 8 or len(set(variables)) != len(variables):
            raise ValueError("Solve admite entre una y ocho variables distintas.")
        domain_name = "Complexes"
        if len(node.children) == 3:
            domain_node = node.children[2]
            if domain_node.kind != "name" or domain_node.value not in (
                "Reals",
                "Complexes",
            ):
                raise ValueError("El dominio de Solve debe ser Reals o Complexes.")
            domain_name = domain_node.value
        local = []
        raw_equations = node.children[0]
        scope = {key: value for key, value in bindings.items() if key not in {str(item) for item in variables}}
        definition_scope = shadowed_definitions(*variables)
        equations = (
            [read(item, local, scope, definition_scope=definition_scope)
             for item in raw_equations.children]
            if raw_equations.kind == "list"
            else [read(raw_equations, local, scope, definition_scope=definition_scope)]
        )
        if (
            not equations
            or len(equations) > 8
            or not all(isinstance(item, sp.Equality) for item in equations)
        ):
            raise ValueError(
                "Solve requiere una igualdad o una lista de hasta ocho igualdades con ==."
            )
        outcome = solve_equations(equations, variables, domain=domain_name)
        state.absorb(outcome)
        domain = sp.S.Reals if domain_name == "Reals" else sp.S.Complexes
        result = _filter_solutions(outcome, variables, local, domain, state)
        state.details["variables"] = [str(item) for item in variables]
        state.details["original_conditions"] = list(condition_text(local))
        state.conditions.extend(
            "Dominio original de las ecuaciones: " + item
            for item in condition_text(local)
        )
        state.details["domain"] = domain_name
        if result is sp.S.EmptySet:
            state.status = "no_solution"
        return result
    if name == "DSolve":
        arity(node, 3)
        symbol = variable(node.children[2])
        dependent_node = node.children[1]
        if (
            dependent_node.kind != "call"
            or len(dependent_node.children) != 1
            or dependent_node.value
            in SCIENTIFIC_CALLS
            | {
                "Sin",
                "Cos",
                "Exp",
                "Log",
                "Sqrt",
                "Simplify",
                "Expand",
                "Plot",
                "Pi",
                "E",
                "Infinity",
            }
            or dependent_node.children[0].kind != "name"
            or dependent_node.children[0].value != str(symbol)
        ):
            raise ValueError(
                "DSolve requiere una función dependiente como y[x] y su variable x."
            )
        dependent = sp.Function(dependent_node.value)(symbol)
        allowed = {dependent_node.value: dependent.func}
        local = []
        raw_equations = node.children[0]
        scope = {key: value for key, value in bindings.items()
                 if key not in (str(symbol), dependent_node.value)}
        definition_scope = shadowed_definitions(symbol, dependent_node.value)
        equations = (
            [read(item, local, scope, allowed, definition_scope=definition_scope)
             for item in raw_equations.children]
            if raw_equations.kind == "list"
            else [read(raw_equations, local, scope, allowed, definition_scope=definition_scope)]
        )
        if (
            not equations
            or len(equations) > 5
            or not all(isinstance(item, sp.Equality) for item in equations)
        ):
            raise ValueError(
                "DSolve requiere una EDO y hasta cuatro condiciones iniciales expresadas con ==."
            )
        points, _ = _initial_domain_checks(equations, dependent, symbol, local)
        outcome = solve_ode(equations, dependent, symbol)
        state.absorb(outcome)
        _solution_domain_checks(outcome, points, dependent, symbol, local, state)
        if local:
            state.details["original_conditions"] = list(condition_text(local))
            state.warnings.append(
                "Las restricciones de la EDO deben conservarse junto a la solución; no se resuelve su dominio global."
            )
        return outcome.value
    raise ValueError(f"Operación científica no admitida: {name}.")
