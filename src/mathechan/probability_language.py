"""Finite probability calls with explicit lexical sampling of observables."""

import sympy as sp
from sympy.logic.boolalg import BooleanFunction
from sympy.core.relational import Relational
from sympy.assumptions.assume import AppliedPredicate

PROBABILITY_CALLS = frozenset({
    "FiniteDistribution", "WeightedDistribution", "BernoulliDistribution",
    "DiscreteUniformDistribution", "States", "Support", "Probabilities",
    "Mean", "Variance", "StandardDeviation", "Entropy", "Probability", "Expectation",
})


def absorb_probability(result, state):
    from .assumptions import combine_assumptions, refine_expression, predicates

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
    from .assumptions import combine_assumptions, refine_expression, predicates
    from .finite_probability import FiniteDistribution, probability_operation, distribution_requirements
    from .language_ops import EvaluationState, arity, checked_restrictions, scalar, variable

    if node.value not in {"Probability", "Expectation"}:
        arguments = tuple(build(child, restrictions, state, bindings, functions, definitions)
                          for child in node.children)
        return absorb_probability(probability_operation(node.value, arguments, state.assumptions), state)

    arity(node, 2)
    specification = node.children[1]
    if specification.kind != "list" or len(specification.children) != 2:
        raise ValueError("Use Probability[evento,{variable,distribución}] o Expectation[expresión,{variable,distribución}].")
    symbol = variable(specification.children[0])
    distribution = build(specification.children[1], restrictions, state, bindings, functions, definitions)
    if not isinstance(distribution, FiniteDistribution):
        raise ValueError("Se requiere una distribución discreta finita.")
    for condition in distribution_requirements(distribution, state.assumptions):
        if condition not in state.requirements:
            state.requirements.append(condition)
            state.conditions.append(sp.sstr(condition))
            state.mark_status("conditional")

    names = {str(symbol)}
    local_definitions = {name: value for name, value in definitions.items() if name not in names}
    # The binder shadows definitions and assumptions about an outer homonym.
    assumptions = sp.And(*(condition for condition in sp.And.make_args(state.assumptions)
                           if symbol not in condition.free_symbols))
    terms = []
    sampled = 0
    for coordinate, probability in zip(distribution.states, distribution.probabilities):
        probability = refine_expression(probability, state.assumptions)
        try:
            zero = sp.ask(sp.Q.zero(probability), predicates(state.assumptions))
        except (ValueError, TypeError, NotImplementedError):
            zero = None
        if probability.is_zero is True or zero is True:
            continue
        if state.sum_terms >= 2000:
            raise ValueError("Las operaciones ligadas exceden 2000 términos compartidos.")
        state.sum_terms += 1
        sampled += 1
        child = EvaluationState(sum_terms=state.sum_terms, assumptions=assumptions,
                                call_depth=state.call_depth, steps=state.steps)
        local = []
        result = build(node.children[0], local, child,
                       {**bindings, str(symbol): coordinate}, functions, local_definitions)
        restrictions.extend(checked_restrictions(local))
        state.steps, state.sum_terms = child.steps, child.sum_terms
        state.mark_status(child.status)
        state.warnings.extend(child.warnings)
        state.conditions.extend(child.conditions)
        state.requirements.extend(child.requirements)
        if node.value == "Probability":
            result = sp.simplify(result)
            if not (result is sp.true or result is sp.false or
                    isinstance(result, (Relational, BooleanFunction, AppliedPredicate, sp.Contains))):
                raise ValueError("Probability requiere un evento lógico, no una expresión escalar.")
            for comparison in result.atoms(sp.core.relational.Relational):
                if comparison.rel_op in {"<", "<=", ">", ">="}:
                    for operand in (comparison.lhs, comparison.rhs):
                        requirement = refine_expression(sp.Contains(operand, sp.S.Reals), state.assumptions)
                        combine_assumptions(state.assumptions, requirement)
                        if requirement is not sp.true and requirement not in state.requirements:
                            state.requirements.append(requirement)
                            state.conditions.append(sp.sstr(requirement))
                            state.mark_status("conditional")
            if result is sp.true:
                terms.append(probability)
            elif result is not sp.false:
                terms.append(sp.Piecewise((probability, result), (0, True)))
        else:
            result = scalar(result)
            if result.has(sp.nan, sp.zoo, sp.oo, -sp.oo) or result.is_finite is False:
                raise ValueError("El observable no es finito en un estado de masa no nula o indecidida.")
            terms.append(probability*result)
    value = sp.simplify(sp.Add(*terms))
    if int(sp.count_ops(value)) > 4096:
        raise ValueError("El resultado probabilístico excede 4096 operaciones.")
    state.details.update(operation=node.value, method="finite_weighted_sum",
                         declared_states=len(distribution.states), sampled_states=sampled,
                         measure="discrete_probability_mass", domain_analysis="partial")
    return value
