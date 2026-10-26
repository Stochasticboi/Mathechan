"""Short calls for finite canonical ensembles with retained physical domains."""

CANONICAL_CALLS = frozenset({
    "Canon", "LogZ", "Dist", "Energy", "FreeEnergy", "HeatCapacity", "Levels", "Degens",
})


def canonical_call(node, build, restrictions, state, bindings, functions, definitions):
    from .canonical import canonical_operation
    from .probability_language import absorb_probability

    arguments = tuple(build(child, restrictions, state, bindings, functions, definitions)
                      for child in node.children)
    return absorb_probability(canonical_operation(node.value, arguments, state.assumptions), state)
