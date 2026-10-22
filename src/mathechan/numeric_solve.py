"""Exact isolation followed by numerical evaluation of bounded QQ polynomials."""

import sympy as sp
from sympy.core.evalf import PrecisionExhausted
from sympy.core.relational import Relational
from sympy.logic.boolalg import BooleanFunction

from .algebra import _rational_expression
from .calculus import OperationOutcome

MAX_NUMERIC_DEGREE = 32


def _precision(value):
    if isinstance(value, bool) or not isinstance(value, (int, sp.Integer)) or not 10 <= value <= 200:
        raise ValueError("NSolve requiere una precisión entera entre 10 y 200 dígitos.")
    return int(value)


def _domain(value):
    if value == "Complexes" or value is sp.S.Complexes:
        return sp.S.Complexes
    if value == "Reals" or value is sp.S.Reals:
        return sp.S.Reals
    raise ValueError("NSolve admite los dominios Reals o Complexes.")


def _truth(condition):
    condition = sp.simplify(condition)
    if condition is sp.true:
        return True
    if condition is sp.false:
        return False
    return None


def _nonzero(value):
    value = sp.simplify(value)
    if value.has(sp.nan, sp.zoo, sp.oo, -sp.oo) or value.is_finite is False:
        return False
    if value.is_zero is True:
        return False
    if value.is_finite is True and value.is_zero is False:
        return True
    if not value.free_symbols and value.is_algebraic is True:
        zero = value.equals(0)
        return None if zero is None else not zero
    return None


def _sample_condition(condition, variable, value, approximate=False, exact_root=None):
    """Sample orders at the rounded point, exact predicates at the isolated root."""
    if isinstance(condition, Relational):
        if approximate and isinstance(condition, sp.Equality):
            return _sample_condition(condition, variable, exact_root)
        left, right = condition.lhs.subs(variable, value), condition.rhs.subs(variable, value)
        if condition.rel_op not in {"==", "!="} and (left.is_real is False or right.is_real is False):
            return sp.false
        return condition.func(left, right)
    if isinstance(condition, BooleanFunction):
        return condition.func(*(_sample_condition(child, variable, value, approximate, exact_root)
                                for child in condition.args))
    if approximate:
        return condition.subs(variable, exact_root)
    return condition.subs(variable, value)


def _allowed(root, variable, restrictions, requirements):
    pending = []
    for restriction in restrictions:
        sampled = restriction.subs(variable, root)
        allowed = _nonzero(sampled)
        if allowed is False:
            return False, ()
        if allowed is None:
            pending.append(sp.Ne(sampled, 0))
    for requirement in requirements:
        sampled = _sample_condition(requirement, variable, root)
        allowed = _truth(sampled)
        if allowed is False:
            return False, ()
        if allowed is None:
            pending.append(sampled)
    return (None if pending else True), tuple(pending)


def _identity(variable, domain, restrictions, requirements, details):
    result = domain
    pending = []
    for item in restrictions:
        if item.free_symbols - {variable}:
            pending.append(sp.Ne(item, 0))
            continue
        allowed = _nonzero(item)
        if allowed is False:
            return OperationOutcome(sp.S.EmptySet, "no_solution", details=details)
        if allowed is True:
            continue
        try:
            _rational_expression(item)
            excluded = sp.solveset(item, variable, domain=domain)
        except (ValueError, NotImplementedError, ArithmeticError):
            pending.append(sp.Ne(item, 0))
            continue
        if excluded.has(sp.ConditionSet):
            pending.append(sp.Ne(item, 0))
        else:
            result = sp.Complement(result, excluded)
    pending.extend(item for item in requirements if _truth(item) is not True)
    condition = sp.And(*pending)
    if condition is sp.false:
        return OperationOutcome(sp.S.EmptySet, "no_solution", details=details)
    if condition is not sp.true:
        result = sp.ConditionSet(variable, condition, result)
    unresolved = result.has(sp.ConditionSet)
    details.update(
        verification="not_applicable_infinite_solution_set",
        completeness={"exact_isolation": "identity", "approximation_certified": False,
                      "conditions_decided": not unresolved},
    )
    return OperationOutcome(
        result, "unresolved" if unresolved else "solved",
        conditions=(sp.sstr(condition),) if condition is not sp.true else (),
        warnings=("La ecuación es una identidad: se conserva el conjunto de soluciones, no una lista numérica finita.",),
        details=details,
    )


def _approximate(root, precision):
    value = root.evalf(precision, strict=True)
    if isinstance(value, sp.Rational):
        value = sp.Float(value, precision)
    if value.free_symbols or value.is_number is not True or value.is_finite is not True:
        raise ValueError("La raíz aislada no produjo una aproximación numérica finita.")
    return value


def _residual(polynomial, original, value, precision, restrictions, requirements, exact_root):
    working = precision + 20
    coefficients = polynomial.all_coeffs()[::-1]
    point = value.evalf(working)
    residual = sp.N(polynomial.as_expr().subs(polynomial.gen, point), working)
    original_residual = sp.N(original.subs(polynomial.gen, point), working)
    original_finite = original_residual.is_finite is True
    domain_checks = [_nonzero(item.subs(polynomial.gen, point)) for item in restrictions]
    domain_checks.extend(_truth(_sample_condition(item, polynomial.gen, point, approximate=True,
                                                 exact_root=exact_root))
                         for item in requirements)
    domain_at_approximation = (False if False in domain_checks else
                               None if None in domain_checks else True)
    radius = sp.Max(1, sp.Abs(point))
    scale = sp.Max(1, sum(sp.Abs(coefficient) * radius ** power
                          for power, coefficient in enumerate(coefficients)))
    normalized = sp.N(sp.Abs(residual) / scale, working)
    threshold = sp.Rational(1, 10) ** (precision - 4)
    passed = (original_finite and domain_at_approximation is not False
              and normalized.is_finite is True and _truth(normalized <= threshold) is True)
    return {
        "original_equation_residual": sp.sstr(original_residual),
        "original_residual_finite": bool(original_finite),
        "domain_at_approximation": domain_at_approximation,
        "polynomial_residual": sp.sstr(residual),
        "normalized_backward_error": sp.sstr(normalized),
        "threshold": sp.sstr(threshold),
        "passed": bool(passed),
    }


def solve_polynomial_numerically(equation, variable, precision=30, domain="Complexes",
                                 restrictions=(), requirements=(), assumptions=sp.true):
    """Solve one exact rational equation, checking exclusions before rounding.

    Isolation completeness is exact. The subsequent normalized residual check is
    a backward-error diagnostic, never a certified bound on individual roots.
    Unresolved conditions retain candidates rather than silently removing them.
    """
    precision, domain = _precision(precision), _domain(domain)
    if not isinstance(variable, sp.Symbol) or variable.is_commutative is not True:
        raise ValueError("NSolve requiere un símbolo escalar como variable.")
    if isinstance(equation, sp.Equality):
        expression = equation.lhs - equation.rhs
    elif isinstance(equation, sp.Expr):
        expression = equation
    else:
        raise ValueError("NSolve requiere una ecuación o una expresión igualada a cero.")
    float_atoms = expression.atoms(sp.Float)
    original_expression = expression
    model = expression.xreplace({item: sp.Rational(item) for item in float_atoms})
    try:
        _rational_expression(model)
    except ValueError:
        from .symbolic_systems import polynomial_preflight
        polynomial_preflight(model, (variable,), maximum_degree=MAX_NUMERIC_DEGREE)
    if expression.free_symbols - {variable}:
        raise ValueError("NSolve requiere una ecuación univariada sin parámetros libres.")
    requirements = tuple(requirements) + (() if assumptions is sp.true else (assumptions,))
    if any(not isinstance(item, sp.Basic) for item in (*restrictions, *requirements)):
        raise ValueError("Las condiciones de NSolve deben ser expresiones simbólicas.")
    numerator, denominator = sp.together(model).as_numer_denom()
    restrictions = tuple(restrictions) + (denominator,)
    polynomial = sp.Poly(numerator, variable, extension=True)
    if any(coefficient.is_algebraic is not True for coefficient in polynomial.all_coeffs()):
        raise ValueError("NSolve sin inicio requiere coeficientes algebraicos o Float finitos.")
    if polynomial.degree() > MAX_NUMERIC_DEGREE:
        raise ValueError("NSolve admite polinomios de grado hasta 32.")
    details = {
        "method": "sympy.Poly.all_roots_exact_isolation_then_evalf",
        "sympy_version": sp.__version__,
        "requested_significant_digits": precision,
        "domain": sp.sstr(domain), "polynomial": sp.sstr(polynomial.as_expr()),
        "residual_model": "numerator_polynomial_normalized_backward_error",
        "exact_roots": [], "multiplicities": [], "residuals": [],
        "verification": "not_checked",
        "coefficient_model": "stored_binary_float_values" if float_atoms else "exact_algebraic",
        "input_float_min_precision_bits": min((item._prec for item in float_atoms), default=None),
        "completeness": {"exact_isolation": False, "approximation_certified": False,
                         "conditions_decided": True},
    }
    if polynomial.is_zero:
        return _identity(variable, domain, restrictions, requirements, details)
    if polynomial.degree() == 0:
        details.update(verification="constant_contradiction")
        details["completeness"]["exact_isolation"] = True
        return OperationOutcome(sp.S.EmptySet, "no_solution", details=details)
    try:
        isolated = polynomial.all_roots(multiple=False, radicals=False)
        if sum(multiplicity for _, multiplicity in isolated) != polynomial.degree():
            raise ValueError("El aislamiento no cubrió el grado completo del polinomio.")
        approximations, conditions = [], []
        for root, multiplicity in isolated:
            if domain is sp.S.Reals:
                if root.is_real is False:
                    continue
                if root.is_real is not True:
                    raise ValueError("No se pudo clasificar exactamente una raíz como real o compleja.")
            allowed, pending = _allowed(root, variable, restrictions, requirements)
            if allowed is False:
                continue
            if pending:
                details["completeness"]["conditions_decided"] = False
                conditions.extend(f"Raíz {sp.sstr(root)}: {sp.sstr(item)}" for item in pending)
            value = _approximate(root, precision)
            approximations.append(value)
            details["exact_roots"].append(sp.sstr(root))
            details["multiplicities"].append(int(multiplicity))
            details["residuals"].append(_residual(polynomial, original_expression, value, precision,
                                                  restrictions, requirements, root))
        result = sp.FiniteSet(*approximations)
    except (PrecisionExhausted, ArithmeticError, TypeError, ValueError, NotImplementedError) as error:
        raise ValueError("NSolve no pudo completar el aislamiento y la evaluación numérica: " + str(error)) from error
    details["completeness"]["exact_isolation"] = True
    warnings = ["El residuo normalizado es un diagnóstico de error hacia atrás; no es una cota certificada del error de las raíces."]
    if float_atoms:
        warnings.append("Los coeficientes Float conservan sus valores binarios y precisión originales; pedir más dígitos no recupera información de entrada ni certifica exactitud física.")
    collisions = len(result) != len(approximations)
    passed = all(item["passed"] for item in details["residuals"])
    details["verification"] = "normalized_residual_passed" if passed else "normalized_residual_failed"
    details["completeness"]["distinct_approximations"] = not collisions
    if collisions:
        warnings.append("Raíces exactas distintas colapsaron en una misma aproximación; aumente la precisión.")
    if not passed:
        warnings.append("Al menos una aproximación no superó la verificación del residuo o del dominio.")
    if any(not item["original_residual_finite"] for item in details["residuals"]):
        warnings.append("Una aproximación cayó en un polo o valor indefinido de la ecuación original; aumente la precisión.")
    domain_checks = [item["domain_at_approximation"] for item in details["residuals"]]
    details["domain_at_approximation"] = (False if False in domain_checks else
                                          None if None in domain_checks else True)
    if details["domain_at_approximation"] is False:
        warnings.append("Una aproximación viola una exclusión original del dominio; aumente la precisión.")
    if conditions:
        warnings.append("Se conservan candidatos sujetos a condiciones no decididas exactamente.")
    status = ("unverified" if collisions or not passed else "conditional" if conditions
              else "no_solution" if result is sp.S.EmptySet else "approximate")
    return OperationOutcome(result, status, tuple(dict.fromkeys(conditions)), tuple(warnings), details)


def solve_numerically(equation, variable, precision=30, domain="Complexes", restrictions=(),
                      requirements=(), assumptions=sp.true, initial=None):
    """Enumerate polynomial roots, or explicitly request a local seeded solve."""
    if initial is None and isinstance(variable, sp.Symbol):
        return solve_polynomial_numerically(equation, variable, precision, domain,
                                             restrictions, requirements, assumptions)
    from .numeric_systems import solve_system_numerically
    return solve_system_numerically(equation, variable, precision, domain,
                                    restrictions, requirements, assumptions, initial)
