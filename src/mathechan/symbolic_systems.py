"""Bounded polynomial systems and explicit-domain reduction of conditions."""

import sympy as sp
from sympy.core.relational import Relational

from .algebra import _rational_shape
from .calculus import OperationOutcome, _domain, _equations


def system_input(equations, variables):
    expressions = _equations(equations)
    variables = tuple(variables) if isinstance(variables, (tuple, list, sp.Tuple)) else (variables,)
    if not 1 <= len(variables) <= 8 or not 1 <= len(expressions) <= 8:
        raise ValueError("Se admiten de 1 a 8 variables y ecuaciones.")
    if any(not isinstance(item, sp.Symbol) for item in variables) or len(set(variables)) != len(variables):
        raise ValueError("Se requieren símbolos distintos como variables.")
    return expressions, variables


def polynomial_preflight(expression, variables, maximum_degree=8):
    """Bound expansion using rational placeholders for numerical coefficients."""
    replacements = {item: sp.Integer(2) for item in expression.atoms(sp.Number, sp.NumberSymbol)
                    if not isinstance(item, sp.Rational)}
    shape = expression.xreplace(replacements)
    # Algebraic coefficients, such as sqrt(2), are constants with respect to variables.
    def estimate(item):
        if not item.free_symbols & set(variables):
            if item.is_finite is False or item.has(sp.nan, sp.zoo, sp.oo, -sp.oo):
                raise ValueError("Los coeficientes deben ser finitos.")
            return sp.Integer(2)
        if isinstance(item, sp.Pow):
            return sp.Pow(estimate(item.base), item.exp, evaluate=False)
        if isinstance(item, (sp.Add, sp.Mul)):
            return item.func(*(estimate(child) for child in item.args), evaluate=False)
        return item.func(*(estimate(child) for child in item.args)) if item.args else item
    _rational_shape(estimate(shape))
    numerator, denominator = sp.together(expression).as_numer_denom()
    try:
        for item in (numerator, denominator):
            polynomial = sp.Poly(item, *variables)
            if polynomial.total_degree() > maximum_degree or len(polynomial.terms()) > 4096:
                raise ValueError(f"El sistema admite grado total hasta {maximum_degree} y 4096 términos.")
    except sp.PolynomialError as error:
        raise ValueError("Se requieren ecuaciones polinómicas o racionales en las variables.") from error
    return numerator, denominator


def condition_system(expressions, variables, domain, method="sympy.nonlinsolve"):
    base = domain if len(variables) == 1 else sp.ProductSet(*([domain] * len(variables)))
    symbol = variables[0] if len(variables) == 1 else sp.Tuple(*variables)
    condition = sp.And(*(sp.Eq(item, 0) for item in expressions))
    return OperationOutcome(sp.ConditionSet(symbol, condition, base), "unresolved",
        warnings=("Se conserva el sistema condicionado; las ramas degeneradas o su completitud no están decididas.",),
        details={"method": method, "verification": "not_checked", "completeness": False,
                 "solution_kind": "conditional"})


def solve_parameter_branches(equation, variable, domain="Complexes"):
    """Expose the complete coefficient-degeneracy partition for degree 1 or 2."""
    expressions, variables = system_input(equation, variable)
    domain = _domain(domain)
    if len(expressions) != 1 or len(variables) != 1:
        raise ValueError("Las ramas acotadas requieren una ecuación y una variable.")
    expression = expressions[0]
    numerator, denominator = polynomial_preflight(expression, variables, maximum_degree=256)
    polynomial = sp.Poly(numerator, variable)
    outcome = condition_system(expressions, variables, domain, "coefficient_degeneracy_branches")
    if denominator != 1 or polynomial.degree() not in (1, 2):
        return outcome
    def solution(*values):
        return sp.Intersection(sp.FiniteSet(*values), domain)
    if polynomial.degree() == 1:
        a, b = polynomial.all_coeffs()
        branches = [(sp.Ne(a, 0), solution(-b/a)),
                    (sp.And(sp.Eq(a, 0), sp.Eq(b, 0)), domain),
                    (sp.And(sp.Eq(a, 0), sp.Ne(b, 0)), sp.S.EmptySet)]
    else:
        a, b, c = polynomial.all_coeffs()
        delta = b*b - 4*a*c
        branches = [(sp.Ne(a, 0), solution((-b-sp.sqrt(delta))/(2*a), (-b+sp.sqrt(delta))/(2*a))),
                    (sp.And(sp.Eq(a, 0), sp.Ne(b, 0)), solution(-c/b)),
                    (sp.And(sp.Eq(a, 0), sp.Eq(b, 0), sp.Eq(c, 0)), domain),
                    (sp.And(sp.Eq(a, 0), sp.Eq(b, 0), sp.Ne(c, 0)), sp.S.EmptySet)]
    outcome.details.update(branches=[{"condition": sp.sstr(condition), "solution": sp.sstr(value)}
                                    for condition, value in branches if condition is not sp.false],
                           branches_cover_coefficient_cases=True, branch_budget=8)
    return outcome


def solve_polynomial_system(equations, variables, domain="Complexes"):
    expressions, variables = system_input(equations, variables)
    domain = _domain(domain)
    for expression in expressions:
        polynomial_preflight(expression, variables)
    if set().union(*(item.free_symbols for item in expressions)) - set(variables):
        return condition_system(expressions, variables, domain)
    if any(item.has(sp.Float) for item in expressions):
        raise ValueError("Solve requiere coeficientes exactos; use NSolve para datos aproximados.")
    try:
        result = sp.nonlinsolve(expressions, variables)
    except (NotImplementedError, ValueError, sp.PolynomialError):
        return condition_system(expressions, variables, domain)
    details = {"method": "sympy.nonlinsolve", "verification": "not_checked",
               "completeness": False, "sympy_version": sp.__version__}
    warnings = ["La sustitución verifica los candidatos; no certifica por sí sola completitud de todas las ramas."]
    if result is sp.S.EmptySet:
        details.update(verification="empty_set", solution_kind="empty")
        return OperationOutcome(result, "no_solution", warnings=tuple(warnings), details=details)
    if not isinstance(result, sp.FiniteSet) or result.has(sp.ConditionSet):
        return condition_system(expressions, variables, domain)
    checks, infinite, unknown_domain, verified = [], False, False, True
    kept = []
    for candidate in result:
        if not isinstance(candidate, sp.Tuple) or len(candidate) != len(variables):
            return condition_system(expressions, variables, domain)
        if any(isinstance(item, sp.Set) for item in candidate):
            return condition_system(expressions, variables, domain)
        if domain is sp.S.Reals and any(item.is_real is False for item in candidate):
            continue
        unknown_domain |= domain is sp.S.Reals and any(item.is_real is None for item in candidate)
        infinite |= any(item.free_symbols & set(variables) for item in candidate)
        mapping = dict(zip(variables, candidate))
        residuals = [sp.simplify(item.subs(mapping, simultaneous=True)) for item in expressions]
        checks.append([sp.sstr(item) for item in residuals])
        verified &= all(item.is_zero is True for item in residuals)
        if any(item.has(sp.nan, sp.zoo, sp.oo, -sp.oo) or item.is_zero is False for item in residuals):
            return condition_system(expressions, variables, domain)
        kept.append(candidate)
    result = sp.FiniteSet(*kept)
    if unknown_domain:
        result = sp.Intersection(result, sp.ProductSet(*([domain] * len(variables))))
    details.update(verification="verified" if verified else "unverified", residuals=checks,
                   solution_kind="infinite_family" if infinite else "finite_candidates")
    status = ("no_solution" if result is sp.S.EmptySet else "unverified" if not verified
              else "conditional" if infinite or unknown_domain else "evaluated")
    if infinite:
        warnings.append("Las tuplas contienen variables libres y representan familias, no puntos aislados.")
    return OperationOutcome(result, status, warnings=tuple(warnings), details=details)


def reduce_conditions(condition, variables, domain="Reals"):
    variables = tuple(variables) if isinstance(variables, (tuple, list, sp.Tuple)) else (variables,)
    if not 1 <= len(variables) <= 8 or any(not isinstance(item, sp.Symbol) for item in variables):
        raise ValueError("Reduce requiere de 1 a 8 símbolos como variables.")
    domain = _domain(domain)
    if condition not in (sp.true, sp.false) and not isinstance(condition, (Relational, sp.logic.boolalg.BooleanFunction, sp.Contains)):
        raise ValueError("Reduce requiere una condición lógica o una comparación.")
    base = domain if len(variables) == 1 else sp.ProductSet(*([domain] * len(variables)))
    symbol = variables[0] if len(variables) == 1 else sp.Tuple(*variables)
    details = {"method": "bounded_condition_reduction", "domain": sp.sstr(domain), "completeness": False}
    unresolved = lambda: OperationOutcome(sp.ConditionSet(symbol, condition, base), "unresolved",
        warnings=("Reduce conserva condiciones que el solucionador acotado no ha decidido.",), details=details)
    if condition is sp.true or condition is sp.false:
        return OperationOutcome(base if condition is sp.true else sp.S.EmptySet,
                                "evaluated" if condition is sp.true else "no_solution", details=details)
    if len(variables) != 1 or condition.free_symbols - set(variables):
        return unresolved()
    variable = variables[0]
    try:
        if domain is sp.S.Reals:
            def real_set(item):
                if item is sp.true or item is sp.false:
                    return domain if item is sp.true else sp.S.EmptySet
                if isinstance(item, Relational):
                    polynomial_preflight(item.lhs-item.rhs, variables, maximum_degree=32)
                    return sp.Intersection(domain, sp.reduce_inequalities([item], variable).as_set())
                if isinstance(item, sp.And):
                    return sp.Intersection(*(real_set(child) for child in item.args))
                if isinstance(item, sp.Or):
                    return sp.Union(*(real_set(child) for child in item.args))
                if isinstance(item, sp.Not):
                    return sp.Complement(domain, real_set(item.args[0]))
                if isinstance(item, sp.Contains) and item.args[0] == variable:
                    return sp.Intersection(domain, item.args[1])
                raise NotImplementedError
            result = real_set(condition)
        else:
            def complex_set(item):
                if item is sp.true or item is sp.false:
                    return domain if item is sp.true else sp.S.EmptySet
                if isinstance(item, (sp.Equality, sp.Unequality)):
                    polynomial_preflight(item.lhs-item.rhs, variables, maximum_degree=32)
                    roots = sp.solveset(item.lhs - item.rhs, variable, domain=domain)
                    return roots if isinstance(item, sp.Equality) else sp.Complement(domain, roots)
                if isinstance(item, sp.And):
                    return sp.Intersection(*(complex_set(child) for child in item.args))
                if isinstance(item, sp.Or):
                    return sp.Union(*(complex_set(child) for child in item.args))
                if isinstance(item, sp.Not):
                    return sp.Complement(domain, complex_set(item.args[0]))
                if isinstance(item, sp.Contains) and item.args[0] == variable:
                    return sp.Intersection(domain, item.args[1])
                raise NotImplementedError
            result = complex_set(condition)
    except (NotImplementedError, TypeError, ValueError):
        return unresolved()
    details.update(completeness=not result.has(sp.ConditionSet), verification="symbolic_set_reduction")
    return OperationOutcome(result, "unresolved" if result.has(sp.ConditionSet)
                            else "no_solution" if result is sp.S.EmptySet else "evaluated", details=details)
