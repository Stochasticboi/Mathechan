"""Language integration for bounded dense linear algebra."""

import sympy as sp

LINEAR_CALLS = frozenset({
    "Dimensions", "Dot", "Transpose", "Tr", "Det", "Inverse", "MatrixRank",
    "LinearSolve", "Eigenvalues", "Eigenvectors", "MatrixPower", "MatrixExp",
})
SPECTRAL_CALLS = frozenset({"Eigenvalues", "Eigenvectors", "MatrixExp"})


def absorb_linear(result, state):
    """Retain executable branch requirements alongside presentation metadata."""
    from .assumptions import combine_assumptions, refine_expression

    outcome, requirements = result
    for condition in requirements:
        condition = refine_expression(condition, state.assumptions)
        combine_assumptions(state.assumptions, condition)
        if condition is not sp.true:
            if condition not in state.requirements:
                state.requirements.append(condition)
            state.conditions.append(sp.sstr(condition))
            state.mark_status("conditional")
    state.absorb(outcome)
    return outcome.value


def matrix_call(node, build, restrictions, state, bindings, functions, definitions):
    arguments = tuple(build(child, restrictions, state, bindings, functions, definitions)
                      for child in node.children)
    if node.value == "Dot" and len(arguments) > 2:
        from .linear_algebra import matrix_operation
        value = arguments[0]
        for argument in arguments[1:]:
            value = absorb_linear(matrix_operation("Dot", (value, argument), state.assumptions), state)
        return value
    if node.value in SPECTRAL_CALLS:
        from .matrix_spectral import spectral_operation
        result = spectral_operation(node.value, arguments, state.assumptions)
    else:
        from .linear_algebra import matrix_operation
        result = matrix_operation(node.value, arguments, state.assumptions)
    return absorb_linear(result, state)


def matrix_binary(operator, left, right, state):
    from .linear_algebra import bounded_binary
    return absorb_linear(bounded_binary(operator, left, right, state.assumptions), state)


def numerical_container(value, precision):
    """Approximate at most 64 scalar entries without evaluating stored source."""
    from .algebra import numerical

    if not isinstance(precision, sp.Integer) or not 1 <= precision <= 1000:
        raise ValueError("La precisión debe ser un entero entre 1 y 1000.")
    count = 0

    def convert(item):
        nonlocal count
        if isinstance(item, sp.MatrixBase):
            return item.applyfunc(convert).as_immutable()
        if isinstance(item, sp.Tuple):
            return sp.Tuple(*(convert(child) for child in item))
        count += 1
        if count > 64:
            raise ValueError("N admite hasta 64 entradas escalares en un contenedor.")
        return numerical(item, precision)

    result = convert(value)
    if not count:
        raise ValueError("N requiere al menos una entrada numérica.")
    return result
