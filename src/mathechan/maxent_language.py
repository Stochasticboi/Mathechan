"""Language boundary for finite maximum-entropy inference and diagnostics."""

MAXENT_CALLS = frozenset({
    "MaxEnt", "RelEntropy", "Means", "Targets", "Residuals", "Dual", "FaceDual",
    "DualGap", "Active", "Rank", "Converged", "Score",
})


def maxent_call(node, build, restrictions, state, bindings, functions, definitions):
    from .maxent import maxent_operation
    from .probability_language import absorb_probability

    arguments = tuple(build(child, restrictions, state, bindings, functions, definitions)
                      for child in node.children)
    return absorb_probability(maxent_operation(node.value, arguments, state.assumptions), state)
