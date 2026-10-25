"""Finite probability calls with explicit lexical sampling of observables."""

import sympy as sp

PROBABILITY_CALLS = frozenset({
    "FiniteDistribution", "WeightedDistribution", "BernoulliDistribution",
    "DiscreteUniformDistribution", "States", "Support", "Probabilities",
    "Mean", "Variance", "StandardDeviation", "Entropy", "Probability", "Expectation",
    "JointFiniteDistribution", "MarginalDistribution", "ConditionalDistribution",
    "Covariance", "Correlation",
})


def absorb_probability(result, state):
    from .assumptions import combine_assumptions, refine_expression

    outcome, requirements = result
    for condition in requirements:
        try:
            condition = refine_expression(condition, state.assumptions)
        except ValueError:
            pass  # An undecidable membership predicate remains an explicit requirement.
        combine_assumptions(state.assumptions, condition)
        if condition is not sp.true:
            if condition not in state.requirements:
                state.requirements.append(condition)
            state.conditions.append(sp.sstr(condition))
            state.mark_status("conditional")
    state.absorb(outcome)
    return outcome.value


def probability_call(node, build, restrictions, state, bindings, functions, definitions):
    from .finite_probability import probability_operation
    from .joint_probability import JointFiniteDistribution, joint_operation

    if node.value in {"Probability", "Expectation", "ConditionalDistribution", "Covariance", "Correlation"}:
        from .probability_sampling import bound_probability_call
        return bound_probability_call(node, build, restrictions, state, bindings, functions, definitions)
    arguments = tuple(build(child, restrictions, state, bindings, functions, definitions)
                      for child in node.children)
    if (node.value in {"JointFiniteDistribution", "MarginalDistribution"}
            or arguments and isinstance(arguments[0], JointFiniteDistribution)):
        result = joint_operation(node.value, arguments, state.assumptions)
    else:
        result = probability_operation(node.value, arguments, state.assumptions)
    return absorb_probability(result, state)
