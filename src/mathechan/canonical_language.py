"""Short calls for finite canonical ensembles with retained physical domains."""

CANONICAL_CALLS = frozenset({
    "Canon", "LogZ", "Dist", "Energy", "FreeEnergy", "HeatCapacity", "Levels", "Degens",
})


def canonical_call(node, build, restrictions, state, bindings, functions, definitions):
    from .canonical import canonical_operation
    from .probability_language import absorb_probability

    arguments = tuple(build(child, restrictions, state, bindings, functions, definitions)
                      for child in node.children)
    from .maxent import MaxEntResult, maxent_operation
    if arguments and isinstance(arguments[0], MaxEntResult):
        return absorb_probability(maxent_operation(node.value, arguments, state.assumptions), state)
    return absorb_probability(canonical_operation(node.value, arguments, state.assumptions), state)
