"""Admitted hyperbolic functions and conservative pole tracking."""

import sympy as sp

HYPERBOLIC_FUNCTIONS = {
    "Sinh": sp.sinh, "Cosh": sp.cosh, "Tanh": sp.tanh,
    "Coth": sp.coth, "Sech": sp.sech, "Csch": sp.csch,
    "ArcSinh": sp.asinh, "ArcCosh": sp.acosh, "ArcTanh": sp.atanh,
    "ArcCoth": sp.acoth, "ArcSech": sp.asech, "ArcCsch": sp.acsch,
}


def track_hyperbolic_domain(name, argument, restrictions, state):
    from .domains import require_nonzero

    if (not isinstance(argument, sp.Expr) or argument.is_commutative is not True
            or argument.has(sp.nan, sp.zoo, sp.oo, -sp.oo)):
        raise ValueError("Las funciones hiperbólicas requieren un argumento escalar finito.")
    excluded = None
    if name in {"Tanh", "Sech"}:
        excluded = sp.cosh(argument)
    elif name in {"Coth", "Csch"}:
        excluded = sp.sinh(argument)
    elif name in {"ArcTanh", "ArcCoth"}:
        excluded = 1-argument**2
    elif name in {"ArcSech", "ArcCsch"}:
        excluded = argument
    if excluded is not None:
        if excluded.is_zero is True:
            raise ValueError(f"{name} no es finita en este punto.")
        require_nonzero(excluded, restrictions)
    if name.startswith("Arc"):
        state.warnings.append(
            f"{name} usa la rama principal compleja; el seguimiento de cortes de rama y diferenciabilidad es parcial."
        )


def track_hyperbolic_derivative(expression, value, restrictions):
    """Keep explicit derivative denominators before later arithmetic cancels them."""
    from .domains import require_nonzero

    if not expression.has(*HYPERBOLIC_FUNCTIONS.values()):
        return
    for term in sp.preorder_traversal(value):
        if isinstance(term, sp.Pow) and term.exp.is_negative is True:
            require_nonzero(term.base, restrictions)


def simplify_hyperbolic_residual(expression, residual):
    """Verify small hyperbolic identities through their exponential definitions."""
    if (residual != 0 and expression.has(*HYPERBOLIC_FUNCTIONS.values())
            and sp.count_ops(residual) <= 128):
        rewritten = residual.rewrite(sp.exp)
        if sp.count_ops(rewritten) <= 512:
            try:
                simplified = sp.cancel(rewritten)
            except (ValueError, TypeError, NotImplementedError, sp.PolynomialError):
                return residual
            if simplified == 0:
                return sp.S.Zero
    return residual
