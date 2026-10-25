"""Short names for bounded complex linear algebra and subsystem traces."""

QUANTUM_CORE_CALLS = frozenset({
    "Conj", "Re", "Im", "Adj", "Inner", "Norm", "Unit", "Dyad", "Proj", "Kron", "Ortho",
})
QUANTUM_CHECK_CALLS = frozenset({"HermQ", "UnitaryQ", "PSDCheck", "PTrace"})
QUANTUM_CALLS = QUANTUM_CORE_CALLS | QUANTUM_CHECK_CALLS


def quantum_call(node, build, restrictions, state, bindings, functions, definitions):
    from .matrix_language import absorb_linear

    arguments = tuple(build(child, restrictions, state, bindings, functions, definitions)
                      for child in node.children)
    if node.value in QUANTUM_CHECK_CALLS:
        from .quantum_checks import check_operation
        result = check_operation(node.value, arguments, state.assumptions)
    else:
        from .quantum_algebra import quantum_operation
        result = quantum_operation(node.value, arguments, state.assumptions)
    return absorb_linear(result, state)
