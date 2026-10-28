"""Language boundary for finite entropy functionals and real q-functions."""

GENERALIZED_CALLS = frozenset({"Renyi", "Tsallis", "KL", "Escort", "QExp", "QLog"})


def generalized_call(node, build, restrictions, state, bindings, functions, definitions):
    from .probability_language import absorb_probability

    arguments = tuple(build(child, restrictions, state, bindings, functions, definitions)
                      for child in node.children)
    if node.value in {"QExp", "QLog"}:
        from .q_functions import q_operation
        result = q_operation(node.value, arguments, state.assumptions)
    else:
        from .generalized_entropy import entropy_operation
        result = entropy_operation(node.value, arguments, state.assumptions)
    return absorb_probability(result, state)
