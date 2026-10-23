"""Evaluation rules for bounded scientific operations over the existing AST."""

from dataclasses import dataclass, field

import sympy as sp

from .matrix_language import LINEAR_CALLS

from .domains import condition_text, require_nonzero

SCIENTIFIC_CALLS = LINEAR_CALLS | frozenset(
    {
        "N",
        "If",
        "FullSimplify",
        "AnalyzeDomain",
        "CertifiedN",
        "Reduce",
        "Factor",
        "Together",
        "Cancel",
        "Collect",
        "Apart",
        "Substitute",
        "ReplaceAll", "Rule", "RuleDelayed",
        "Sum",
        "Integrate",
        "Series", "Normal", "Product", "Grad", "Div", "Curl", "Jacobian", "Hessian",
        "Limit",
        "Solve",
        "NSolve",
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
    assumptions: object = sp.true
    call_depth: int = 0
    steps: int = 0

    def mark_status(self, status):
        priority = {
            "evaluated": 0,
            "verified": 1,
            "conditional": 2,
            "series": 3,
            "unverified": 3,
            "unresolved": 4,
            "no_solution": 5,
            "divergent": 6,
            "no_limit": 7,
        }
        if priority.get(status, 0) > priority.get(self.status, 0):
            self.status = status

    def absorb(self, outcome):
        self.mark_status(outcome.status)
        self.warnings.extend(outcome.warnings)
        self.conditions.extend(outcome.conditions)
        self.details.update(outcome.details)


def variable(node):
    if node.kind != "name" or node.value in (
        "Pi", "E", "Infinity", "Reals", "Complexes", "Integers", "True", "False"
    ):
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
    tuple_candidates = outcome.details.get("method") in ("sympy.linsolve", "sympy.nonlinsolve")
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


def _hypothesis_solutions(result, variables, state):
    """Do not present a candidate excluded by the active mathematical context."""
    condition = sp.And(state.assumptions, *state.requirements)
    if condition is sp.true or not condition.free_symbols.intersection(variables):
        return result
    if isinstance(result, sp.FiniteSet):
        kept = []
        for candidate in result:
            values = tuple(candidate) if isinstance(candidate, sp.Tuple) else (candidate,)
            if len(values) != len(variables):
                state.mark_status("unresolved")
                return result
            verdict = sp.simplify(condition.subs(dict(zip(variables, values)), simultaneous=True))
            if verdict is not sp.false:
                kept.append(candidate)
                if verdict is not sp.true:
                    state.mark_status("conditional")
        return sp.FiniteSet(*kept)
    if len(variables) == 1:
        state.mark_status("unresolved")
        return sp.ConditionSet(variables[0], condition, result)
    state.mark_status("unresolved")
    state.warnings.append("La familia de soluciones conserva hipótesis que no se pudieron filtrar.")
    return result


def _check_integral_hypotheses(symbol, bounds, state):
    """A branch chosen under assumptions must be valid on the whole real interval."""
    for condition in (state.assumptions, *state.requirements):
        if symbol not in condition.free_symbols:
            continue
        normalized = condition.replace(
            lambda item: isinstance(item, sp.Contains) and item.args[0] == symbol
            and item.args[1] in (sp.S.Reals, sp.S.Complexes),
            lambda item: sp.true,
        ).replace(
            lambda item: isinstance(item, sp.Contains) and isinstance(item.args[1], sp.Interval),
            lambda item: item.args[1].as_relational(item.args[0]),
        )
        clauses = [part for part in sp.And.make_args(normalized) if symbol in part.free_symbols]
        if not clauses:
            continue
        try:
            interval = sp.Interval(sp.Min(*bounds), sp.Max(*bounds))
            permitted = sp.reduce_inequalities(clauses, symbol).as_set()
            valid = interval.is_subset(permitted)
        except (ValueError, TypeError, NotImplementedError):
            valid = None
        if valid is not True:
            raise ValueError(
                "No se pueden verificar las hipótesis del integrando en todo el intervalo."
            )


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
    if name in LINEAR_CALLS:
        from .matrix_language import matrix_call
        return matrix_call(node, build, restrictions, state, bindings, functions, definitions)
    from .calculus_language import CALLS, calculus_call
    if name in CALLS:
        return calculus_call(node, build, restrictions, state, bindings, functions, definitions)
    if name == "Limit":
        from .limit_language import evaluate_limit
        return evaluate_limit(node, build, restrictions, state, bindings, functions, definitions)
    if name == "FullSimplify":
        from .assumptions import combine_assumptions
        from .simplification import full_simplify_expression

        arity(node, 1, 2)
        previous = state.assumptions
        if len(node.children) == 2:
            condition = read(node.children[1])
            state.assumptions = combine_assumptions(previous, condition)
            if condition is not sp.true:
                state.requirements.append(condition)
                state.conditions.append(sp.sstr(condition))
                state.mark_status("conditional")
        local = []
        try:
            expression = scalar(read(node.children[0], local))
            outcome = full_simplify_expression(expression, state.assumptions,
                                               restrictions=tuple(local),
                                               requirements=tuple(state.requirements))
        finally:
            state.assumptions = previous
        restrictions.extend(local)
        state.absorb(outcome)
        return outcome.value
    if name == "CertifiedN":
        from .certified_numeric import certified_numerical

        arity(node, 1, 2)
        precision = read(node.children[1]) if len(node.children) == 2 else sp.Integer(30)
        outcome = certified_numerical(scalar(read(node.children[0])), precision)
        state.absorb(outcome)
        return outcome.value
    if name in ("AnalyzeDomain", "Reduce"):
        arity(node, 2, 3)
        specification = node.children[1]
        variables = ([variable(child) for child in specification.children]
                     if specification.kind == "list" else [variable(specification)])
        if not variables or len(variables) > 8 or len(set(variables)) != len(variables):
            raise ValueError("Se requieren de una a ocho variables distintas.")
        domain_name = "Reals"
        if len(node.children) == 3:
            domain_node = node.children[2]
            if domain_node.kind != "name" or domain_node.value not in ("Reals", "Complexes"):
                raise ValueError("El dominio debe ser Reals o Complexes.")
            domain_name = domain_node.value
        scope = {key: item for key, item in bindings.items()
                 if key not in {str(symbol) for symbol in variables}}
        local = []
        expression = read(node.children[0], local, scope,
                          definition_scope=shadowed_definitions(*variables))
        if name == "AnalyzeDomain":
            from .domain_analysis import analyze_domain

            if len(variables) != 1:
                raise ValueError("AnalyzeDomain admite una variable por consulta.")
            outcome = analyze_domain(scalar(expression), variables[0], domain_name,
                                     restrictions=tuple(local),
                                     requirements=tuple(state.requirements) + (state.assumptions,))
        else:
            from .symbolic_systems import reduce_conditions

            if isinstance(expression, sp.Tuple):
                expression = sp.And(*expression)
            condition = sp.And(expression, state.assumptions, *state.requirements,
                               *(sp.Ne(item, 0) for item in local))
            outcome = reduce_conditions(condition, variables, domain_name)
        state.absorb(outcome)
        state.details["original_conditions"] = list(condition_text(local))
        return outcome.value
    if name in ("Factor", "Together", "Cancel"):
        arity(node, 1)
        operation = {
            "Factor": algebra.factor_expression,
            "Together": algebra.together_expression,
            "Cancel": algebra.cancel_expression,
        }[name]
        return operation(scalar(read(node.children[0])))
    if name in ("Collect", "Apart"):
        arity(node, 2)
        symbol = variable(node.children[1])
        scope = {key: value for key, value in bindings.items() if key != str(symbol)}
        local = []
        expression = scalar(read(node.children[0], local, scope=scope,
                                 definition_scope=shadowed_definitions(symbol)))
        operation = algebra.collect_expression if name == "Collect" else algebra.apart_expression
        result = operation(expression, symbol)
        if name == "Apart":
            result, branches = algebra.apart_parameter_branches(expression, symbol, result)
            if branches:
                state.mark_status("conditional")
                state.details["apart_branches"] = list(branches)
                state.warnings.append("Apart conserva la rama genérica y el caso degenerado del parámetro en Piecewise.")
            parameter_conditions = []
            for term in sp.Add.make_args(result):
                denominator = term.as_numer_denom()[1]
                require_nonzero(denominator, local)
                for factor, _ in sp.factor_list(denominator)[1]:
                    if factor.free_symbols and symbol not in factor.free_symbols:
                        parameter_conditions.append(factor)
            if parameter_conditions:
                state.mark_status("conditional")
                state.details["apart_parameter_exclusions"] = list(condition_text(parameter_conditions))
                state.warnings.append(
                    "La descomposición requiere las exclusiones de parámetros indicadas; "
                    "para casos degenerados, sustituya los parámetros antes de usar Apart."
                )
        restrictions.extend(checked_restrictions(
            [substitute_bindings(item, bindings) for item in local]
        ))
        return substitute_bindings(result, bindings)
    if name == "N":
        arity(node, 1, 2)
        precision = (
            read(node.children[1]) if len(node.children) == 2 else sp.Integer(15)
        )
        expression = read(node.children[0])
        if isinstance(expression, (sp.MatrixBase, sp.Tuple)):
            from .matrix_language import numerical_container
            value = numerical_container(expression, precision)
        else:
            value = algebra.numerical(scalar(expression), precision)
        if expression.has(sp.Float):
            state.warnings.append("La precisión solicitada no recupera información perdida en los datos aproximados de entrada.")
        state.details.setdefault("numeric_evaluations", []).append(
            {
                "requested_significant_digits": int(precision),
                "approximate": True,
            }
        )
        return value
    if name == "Substitute":
        arity(node, 3)
        symbol = variable(node.children[1])
        scope = {key: value for key, value in bindings.items() if key != str(symbol)}
        local = []
        child_state = EvaluationState(sum_terms=state.sum_terms, assumptions=state.assumptions,
                                      call_depth=state.call_depth, steps=state.steps)
        expression = scalar(
            read(node.children[0], local, scope, child_state=child_state,
                 definition_scope=shadowed_definitions(symbol))
        )
        state.sum_terms = child_state.sum_terms
        state.steps = child_state.steps
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
            or "aproximación truncada" in item or "O conserva" in item
        )
        if result.has(sp.Integral, sp.ConditionSet, sp.Sum, sp.Product, sp.Limit, sp.Derivative):
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
        if child_state.status == "series" or result.has(sp.Order):
            state.mark_status("series")
        return substitute_bindings(result, bindings)
    if name == "Integrate":
        from .integration_language import integration_call
        return integration_call(node, build, restrictions, state, bindings, functions, definitions)
    if name == "NSolve":
        from .numeric_solve import solve_numerically
        from .numeric_systems import solve_system_numerically

        arity(node, 2, 3, 4, 5)
        variable_node = node.children[1]
        variables = ([variable(child) for child in variable_node.children]
                     if variable_node.kind == "list" else [variable(variable_node)])
        if not variables or len(variables) > 8 or len(set(variables)) != len(variables):
            raise ValueError("NSolve requiere de una a ocho variables distintas.")
        domain_name, precision = "Complexes", sp.Integer(30)
        initial = None
        if len(node.children) >= 3:
            option = node.children[2]
            if option.kind == "name" and option.value in ("Reals", "Complexes"):
                domain_name = option.value
            elif option.kind == "list" and len(node.children) <= 4:
                initial = tuple(read(child) for child in option.children)
            elif len(node.children) == 3:
                precision = read(option)
            else:
                raise ValueError("Use NSolve[ecuación,variable,Reals o Complexes,precisión].")
        if len(node.children) >= 4:
            precision = read(node.children[3])
        if len(node.children) == 5:
            seed = node.children[4]
            if seed.kind != "list":
                raise ValueError("La aproximación inicial debe ser una lista.")
            initial = tuple(read(child) for child in seed.children)
        local = []
        scope = {key: value for key, value in bindings.items()
                 if key not in {str(symbol) for symbol in variables}}
        raw = node.children[0]
        equations = ([read(child, local, scope, definition_scope=shadowed_definitions(*variables))
                      for child in raw.children] if raw.kind == "list" else
                     [read(raw, local, scope, definition_scope=shadowed_definitions(*variables))])
        if not equations or not all(isinstance(equation, sp.Equality) for equation in equations):
            raise ValueError("NSolve requiere ecuaciones con ==.")
        options = dict(restrictions=tuple(local), requirements=tuple(state.requirements),
                       assumptions=state.assumptions, initial=initial)
        if len(variables) == 1 and len(equations) == 1:
            outcome = solve_numerically(equations[0], variables[0], precision, domain_name, **options)
        else:
            outcome = solve_system_numerically(equations, variables, precision, domain_name, **options)
        state.absorb(outcome)
        state.details["variables"] = [str(symbol) for symbol in variables]
        state.details["original_conditions"] = list(condition_text(local))
        state.conditions.extend("Dominio original de la ecuación: " + item
                                for item in condition_text(local))
        return outcome.value
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
        result = _hypothesis_solutions(result, variables, state)
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
        from .kernel import FUNCTIONS
        from .assumptions import ASSUMPTION_CALLS
        from .semantic_types import SEMANTIC_CALLS

        arity(node, 3)
        symbol = variable(node.children[2])
        dependent_node = node.children[1]
        if (
            dependent_node.kind != "call"
            or len(dependent_node.children) != 1
            or dependent_node.value
            in SCIENTIFIC_CALLS | frozenset(FUNCTIONS) | ASSUMPTION_CALLS | SEMANTIC_CALLS
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
