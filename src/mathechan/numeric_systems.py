"""Finite algebraic candidates or explicitly seeded local numerical solutions."""

import sympy as sp

from .calculus import OperationOutcome
from .numeric_solve import _approximate, _domain, _nonzero, _precision, _sample_condition, _truth
from .symbolic_systems import condition_system, polynomial_preflight, solve_polynomial_system, system_input


def _condition_at(condition, variables, candidate, approximate=False, exact=None):
    for index, (variable, value) in enumerate(zip(variables, candidate)):
        condition = _sample_condition(condition, variable, value, approximate,
                                       None if exact is None else exact[index])
    return _truth(condition)


def _local_condition(condition, variables, candidate, precision):
    """A near-zero numerical equality is undecided, never an exact assertion."""
    if isinstance(condition, sp.And):
        values = [_local_condition(item, variables, candidate, precision) for item in condition.args]
        return False if False in values else None if None in values else True
    if isinstance(condition, sp.Or):
        values = [_local_condition(item, variables, candidate, precision) for item in condition.args]
        return True if True in values else None if None in values else False
    if isinstance(condition, sp.Not):
        value = _local_condition(condition.args[0], variables, candidate, precision)
        return None if value is None else not value
    mapping = dict(zip(variables, (item.evalf(precision+20) for item in candidate)))
    if isinstance(condition, sp.Equality):
        left, right = condition.lhs.subs(mapping, simultaneous=True), condition.rhs.subs(mapping, simultaneous=True)
        difference = sp.N(left-right, precision+20)
        if difference.is_zero is True:
            return True
        if difference.is_finite is not True:
            return None
        threshold = sp.Rational(1,10)**(precision-4)*sp.Max(1,sp.Abs(left),sp.Abs(right))
        return None if _truth(sp.Abs(difference)<=threshold) is True else False
    if isinstance(condition, sp.Contains) and condition.args[1] not in (sp.S.Reals,sp.S.Complexes):
        return None
    return _condition_at(condition, variables, candidate)


def _candidate_domain(candidate, variables, domain, restrictions, requirements, approximate=False, exact=None,
                      local_precision=None):
    mapping = dict(zip(variables, candidate))
    checks = []
    if domain is sp.S.Reals:
        checks.extend(True if item.is_real is True else False if item.is_real is False else None
                      for item in candidate)
    checks.extend(_nonzero(item.subs(mapping, simultaneous=True)) for item in restrictions)
    checks.extend((_local_condition(item, variables, candidate, local_precision)
                   if local_precision is not None else _condition_at(item, variables, candidate, approximate, exact))
                  for item in requirements)
    return False if False in checks else None if None in checks else True


def _residuals(expressions, variables, candidate, precision):
    working = precision + 20
    mapping = dict(zip(variables, (item.evalf(working) for item in candidate)))
    records = []
    threshold = sp.Rational(1, 10)**(precision - 4)
    for expression in expressions:
        value = sp.N(expression.subs(mapping, simultaneous=True), working)
        # For transcendental expressions this is an explicit term scale, not a polynomial condition number.
        terms = sp.Add.make_args(expression)
        scale = sp.Max(1, sum(sp.Abs(sp.N(term.subs(mapping, simultaneous=True), working)) for term in terms))
        normalized = sp.N(sp.Abs(value)/scale, working)
        passed = value.is_finite is True and normalized.is_finite is True and _truth(normalized <= threshold) is True
        records.append({"original_equation_residual": sp.sstr(value),
                        "normalized_residual": sp.sstr(normalized), "threshold": sp.sstr(threshold),
                        "passed": bool(passed)})
    return records


def solve_system_numerically(equations, variables, precision=30, domain="Complexes",
                             restrictions=(), requirements=(), assumptions=sp.true, initial=None):
    expressions, variables = system_input(equations, variables)
    precision, domain = _precision(precision), _domain(domain)
    if set().union(*(item.free_symbols for item in expressions)) - set(variables):
        return condition_system(expressions, variables, domain, "numeric_system_parameters")
    if any(item.has(sp.nan, sp.zoo, sp.oo, -sp.oo) for item in expressions):
        raise ValueError("El sistema numérico requiere ecuaciones finitas.")
    requirements = tuple(requirements) + (() if assumptions is sp.true else (assumptions,))
    restrictions = tuple(restrictions) + tuple(sp.together(item).as_numer_denom()[1] for item in expressions)
    float_atoms = set().union(*(item.atoms(sp.Float) for item in expressions))
    warnings = ["La comprobación de residuos no es una cota certificada del error de la solución."]
    details = {"requested_significant_digits": precision, "completeness": False,
               "domain": sp.sstr(domain), "sympy_version": sp.__version__,
               "input_float_min_precision_bits": min((item._prec for item in float_atoms), default=None)}
    if float_atoms:
        warnings.append("Los datos Float conservan su información original; más dígitos de cálculo no recuperan precisión de entrada.")
    exact_candidates = None
    if initial is None:
        model = [item.xreplace({value: sp.Rational(value) for value in float_atoms}) for item in expressions]
        for item in model:
            numerator, _ = polynomial_preflight(item, variables)
            if any(coefficient.is_algebraic is not True for coefficient in sp.Poly(numerator, *variables).coeffs()):
                raise ValueError("El sistema sin inicio requiere coeficientes algebraicos o Float.")
        outcome = solve_polynomial_system(model, variables, domain)
        details.update(method="sympy.nonlinsolve_then_evalf", symbolic_verification=outcome.details.get("verification"))
        if outcome.value is sp.S.EmptySet:
            return OperationOutcome(sp.S.EmptySet, "no_solution", warnings=tuple(warnings), details=details)
        if (not isinstance(outcome.value, sp.FiniteSet) or outcome.status in {"unresolved", "unverified"}
                or any(any(item.free_symbols or isinstance(item, sp.Set) for item in candidate) for candidate in outcome.value)):
            return OperationOutcome(outcome.value, "unresolved", outcome.conditions,
                tuple(warnings) + outcome.warnings + ("El conjunto no consta de puntos aislados numéricos; no se discretiza una familia continua.",), details)
        exact_candidates = list(outcome.value)
        candidates = [tuple(_approximate(item, precision) for item in candidate) for candidate in exact_candidates]
        warnings.append("La enumeración simbólica previa no constituye una certificación independiente de completitud del sistema.")
    else:
        initial = tuple(initial) if isinstance(initial, (tuple, list, sp.Tuple)) else (initial,)
        initial = tuple(sp.sympify(item) if isinstance(item, (int, float, complex)) and not isinstance(item, bool)
                        else item for item in initial)
        if len(initial) != len(variables) or any(not isinstance(item, sp.Expr) or item.free_symbols
                or item.is_number is not True or item.is_finite is not True for item in initial):
            raise ValueError("Se requiere un inicio numérico finito por variable.")
        if len(expressions) != len(variables):
            raise ValueError("La resolución local requiere igual cantidad de ecuaciones y variables.")
        try:
            result = sp.nsolve(expressions, variables, initial, prec=precision,
                               tol=sp.Rational(1, 10)**(precision - 4), maxsteps=100, verify=False)
        except (ValueError, ArithmeticError, TypeError, NotImplementedError) as error:
            raise ValueError("El solucionador local no convergió desde el inicio indicado: " + str(error)) from error
        candidate = tuple(result) if isinstance(result, sp.MatrixBase) else (result,)
        if len(candidate) != len(variables) or any(item.is_finite is not True for item in candidate):
            raise ValueError("El solucionador local no devolvió valores numéricos finitos.")
        candidates = [tuple(_approximate(item, precision) for item in candidate)]
        details.update(method="sympy.nsolve_local", initial=[sp.sstr(item) for item in initial],
                       local_solution=True)
        warnings.append("La solución depende del inicio: es local y no enumera todas las raíces ni prueba existencia o unicidad global.")
    kept, records, pending = [], [], []
    rejected = False
    for index, candidate in enumerate(candidates):
        exact = exact_candidates[index] if exact_candidates is not None else None
        exact_allowed = (_candidate_domain(exact, variables, domain, restrictions, requirements)
                         if exact is not None else None)
        if exact_allowed is False:
            continue
        point_allowed = _candidate_domain(candidate, variables, domain, restrictions, requirements,
                                          approximate=exact is not None, exact=exact,
                                          local_precision=precision if exact is None else None)
        if point_allowed is False:
            rejected = True
            if exact is None:
                raise ValueError("La solución local viola el dominio o las hipótesis; cambie el inicio.")
        if exact_allowed is None and exact is not None or point_allowed is None:
            pending.append("Candidato " + sp.sstr(sp.Tuple(*candidate)) + ": condiciones de dominio pendientes")
        checks = _residuals(expressions, variables, candidate, precision)
        kept.append(candidate)
        records.append({"candidate": [sp.sstr(item) for item in candidate],
                        "domain_at_approximation": point_allowed, "equations": checks})
    value = sp.FiniteSet(*(sp.Tuple(*candidate) for candidate in kept))
    # A scalar invocation retains the established scalar NSolve shape.
    if len(variables) == 1 and not isinstance(equations, (tuple, list, sp.Tuple)):
        value = sp.FiniteSet(*(candidate[0] for candidate in kept))
    passed = all(item["passed"] for record in records for item in record["equations"])
    collisions = len(value) != len(kept)
    details.update(residuals=records, verification="normalized_residual_passed" if passed else "normalized_residual_failed",
                   distinct_approximations=not collisions, conditions_decided=not pending)
    if exact_candidates is not None:
        details["exact_candidates"] = [[sp.sstr(item) for item in candidate] for candidate in exact_candidates]
    if collisions or rejected or not passed:
        warnings.append("Una aproximación no superó la comprobación del residuo, dominio o distinción de raíces; revise el inicio o aumente la precisión.")
    status = ("unverified" if collisions or rejected or not passed else "conditional" if pending
              else "no_solution" if value is sp.S.EmptySet else "approximate")
    return OperationOutcome(value, status, tuple(pending), tuple(warnings), details)
