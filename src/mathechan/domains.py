"""Conservative nonzero conditions from explicit divisions and negative powers."""

import sympy as sp

from .printer import expression_input


def require_nonzero(expression, restrictions):
    """Keep unresolved conditions before the parent operation can cancel them."""
    if restrictions is None or expression.is_zero is False:
        return
    if expression not in restrictions:
        restrictions.append(expression)


def condition_text(restrictions):
    """Human-readable conditions, separate from executable input strings."""
    return tuple(
        f"({expression_input(item) or sp.sstr(item)}) != 0"
        for item in restrictions
    )


def parameter_domain_conditions(exclusions, variables):
    """Keep parameter degeneracies of cancelled bound-variable denominators."""
    free, requirements = [], []
    symbols = set(variables)
    for item in exclusions:
        if not item.free_symbols & symbols:
            require_nonzero(item, free)
            continue
        if sp.count_ops(item) > 256 or len(item.free_symbols) > 8:
            raise ValueError("La exclusión excede 256 operaciones u ocho símbolos.")
        constant, dependent = sp.factor_terms(item).as_independent(*variables, as_Add=False)
        require_nonzero(constant, free)
        if dependent.free_symbols - symbols:
            if not dependent.is_polynomial(*variables):
                raise ValueError("No se puede verificar la degeneración del denominador paramétrico.")
            from .algebra import _rational_shape
            _, degree, _, _ = _rational_shape(dependent)
            if degree > 32:
                raise ValueError("El denominador paramétrico admite grado total hasta 32.")
            condition = sp.Or(*(sp.Ne(c, 0) for c in sp.Poly(dependent, *variables).coeffs()))
            if condition is sp.false:
                raise ValueError("El denominador es idénticamente nulo.")
            if condition is not sp.true:
                requirements.append(condition)
    return free, requirements


def restrictions_at(restrictions, variable, value, coordinate=None):
    """Check a sample; coordinate is an already validated finite interior float.

    Exact endpoints omit coordinate so their symbolic value is preserved.
    No tolerance or approximate-zero criterion is used.
    """
    for expression in restrictions:
        if expression == variable and coordinate is not None:
            if coordinate == 0.0:
                return "El denominador original es cero"
            continue
        sampled = value if expression == variable else expression.subs(variable, value)
        if sampled.is_zero is True:
            return "El denominador original es cero"
        if sampled.is_finite is True and sampled.is_zero is False:
            continue
        sampled = sampled.evalf()
        if sampled.is_zero is True:
            return "El denominador original es cero"
        if sampled.is_finite is not True or sampled.is_zero is None:
            return "No se pudo comprobar el denominador original"
    return None

