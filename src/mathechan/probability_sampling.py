"""Scoped sampling for finite scalar and joint probability spaces."""

import sympy as sp
from sympy.assumptions.assume import AppliedPredicate
from sympy.core.relational import Relational
from sympy.logic.boolalg import BooleanFunction


def bound_probability_call(node, build, restrictions, state, bindings, functions, definitions):
    from .assumptions import predicates, refine_expression
    from .calculus import OperationOutcome
    from .finite_probability import FiniteDistribution, distribution_requirements
    from .joint_probability import JointFiniteDistribution, joint_requirements, condition_distribution
    from .language_ops import EvaluationState, arity, checked_restrictions, scalar, variable
    from .probability_language import absorb_probability

    two_observables = node.value in {"Covariance", "Correlation"}
    arity(node, 3 if two_observables else 2)
    specification = node.children[-1]
    if specification.kind != "list" or len(specification.children) != 2:
        raise ValueError("Use {x,distribución} o {{x,y,...},distribución} como especificación ligada.")
    raw_names = specification.children[0]
    symbols = tuple(variable(item) for item in raw_names.children) if raw_names.kind == "list" else (variable(raw_names),)
    if not symbols or len(set(symbols)) != len(symbols) or len(symbols) > 4:
        raise ValueError("Se requieren entre una y cuatro variables distintas.")
    distribution = build(specification.children[1], restrictions, state, bindings, functions, definitions)
    from .parametric_probability import ParametricDistribution
    if isinstance(distribution, ParametricDistribution):
        from .parametric_sampling import bound_parametric_call
        return bound_parametric_call(node, distribution, symbols, build, restrictions, state,
                                     bindings, functions, definitions)
    if isinstance(distribution, JointFiniteDistribution):
        dimension = distribution.dimension
        rows = distribution.states
        requirements = joint_requirements(distribution, state.assumptions)
    elif isinstance(distribution, FiniteDistribution):
        dimension = 1
        rows = tuple((coordinate,) for coordinate in distribution.states)
        requirements = distribution_requirements(distribution, state.assumptions)
    else:
        raise ValueError("Se requiere una distribución finita escalar o conjunta.")
    if len(symbols) != dimension:
        raise ValueError("El número de variables debe coincidir con la dimensión de la distribución.")
    absorb_probability((OperationOutcome(distribution), requirements), state)

    names = {str(symbol) for symbol in symbols}
    local_definitions = {name: value for name, value in definitions.items() if name not in names}
    assumptions = sp.And(*(condition for condition in sp.And.make_args(state.assumptions)
                           if not set(symbols) & condition.free_symbols))
    active = []
    flags = []
    sampled = 0

    def require(condition):
        absorb_probability((OperationOutcome(sp.S.Zero), (condition,)), state)

    def sample(raw, row):
        child = EvaluationState(sum_terms=state.sum_terms, assumptions=assumptions,
                                call_depth=state.call_depth, steps=state.steps)
        local = []
        result = build(raw, local, child,
                       {**bindings, **dict(zip(map(str, symbols), row))}, functions, local_definitions)
        restrictions.extend(checked_restrictions(local))
        state.steps, state.sum_terms = child.steps, child.sum_terms
        state.mark_status(child.status)
        state.warnings.extend(child.warnings)
        state.conditions.extend(child.conditions)
        state.requirements.extend(child.requirements)
        return result

    def event(value):
        constants = {}
        for condition in sp.And.make_args(assumptions):
            if isinstance(condition, sp.Equality):
                if isinstance(condition.lhs, sp.Symbol) and not condition.rhs.free_symbols:
                    constants[condition.lhs] = condition.rhs
                elif isinstance(condition.rhs, sp.Symbol) and not condition.lhs.free_symbols:
                    constants[condition.rhs] = condition.lhs
        value = value.subs(constants, simultaneous=True)
        value = sp.simplify(value)
        try:
            value = refine_expression(value, assumptions)
        except ValueError:
            pass
        if not (value is sp.true or value is sp.false or
                isinstance(value, (Relational, BooleanFunction, AppliedPredicate, sp.Contains))):
            raise ValueError("Se requiere un evento lógico, no un escalar.")
        for comparison in value.atoms(Relational):
            if comparison.rel_op in {"<", "<=", ">", ">="}:
                for operand in (comparison.lhs, comparison.rhs):
                    require(sp.Contains(operand, sp.S.Reals))
        try:
            answer = sp.ask(predicates(value), predicates(assumptions))
        except (ValueError, TypeError, NotImplementedError):
            answer = None
        if answer is True:
            return sp.true
        if answer is False:
            return sp.false
        return value

    def observable(value):
        value = scalar(value)
        if value.has(sp.nan, sp.zoo, sp.oo, -sp.oo) or value.is_finite is False:
            raise ValueError("El observable no es finito en un estado de masa no nula o indecidida.")
        if two_observables:
            require(sp.Contains(value, sp.S.Reals))
        return value

    for row, probability in zip(rows, distribution.probabilities):
        probability = refine_expression(probability, state.assumptions)
        try:
            zero = sp.ask(sp.Q.zero(probability), predicates(state.assumptions))
        except (ValueError, TypeError, NotImplementedError):
            zero = None
        if probability.is_zero is True or zero is True:
            flags.append(sp.false)
            continue
        if state.sum_terms >= 2000:
            raise ValueError("Las operaciones ligadas exceden 2000 términos compartidos.")
        state.sum_terms += 1
        sampled += 1
        if node.value in {"Probability", "ConditionalDistribution"}:
            result = event(sample(node.children[0], row))
            if node.value == "ConditionalDistribution":
                if result is not sp.true and result is not sp.false:
                    raise ValueError("El evento condicionado es indecidido; especialice sus parámetros.")
                flags.append(result)
            elif result is sp.true:
                active.append(probability)
            elif result is not sp.false:
                active.append(sp.Piecewise((probability, result), (0, True)))
        elif two_observables:
            active.append((probability, observable(sample(node.children[0], row)),
                           observable(sample(node.children[1], row))))
        else:
            active.append(probability*observable(sample(node.children[0], row)))

    if node.value == "ConditionalDistribution":
        value = absorb_probability(condition_distribution(distribution, flags, state.assumptions), state)
    elif two_observables:
        mean_f = sp.Add(*(p*f for p,f,g in active))
        mean_g = sp.Add(*(p*g for p,f,g in active))
        value = sp.Add(*(p*(f-mean_f)*(g-mean_g) for p,f,g in active))
        if node.value == "Correlation":
            variance_f = sp.simplify(sp.Add(*(p*(f-mean_f)**2 for p,f,g in active)))
            variance_g = sp.simplify(sp.Add(*(p*(g-mean_g)**2 for p,f,g in active)))
            require(sp.Gt(variance_f, 0))
            require(sp.Gt(variance_g, 0))
            value /= sp.sqrt(variance_f*variance_g)
        value = sp.simplify(value)
        state.details.update(moment_convention="population_centered_real_observables",
                             conjugation="none", precision_certified=False)
    else:
        value = sp.simplify(sp.Add(*active))
    if int(sp.count_ops(value)) > 4096:
        raise ValueError("El resultado probabilístico excede 4096 operaciones.")
    state.details.update(operation=node.value, method="finite_weighted_sum",
                         declared_states=len(rows), sampled_states=sampled, dimension=dimension,
                         measure="discrete_probability_mass", domain_analysis="partial")
    return value
