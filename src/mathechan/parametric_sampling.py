"""Univariate probability events and scoped expectations for named families."""

import sympy as sp
from sympy.core.relational import Relational

from .calculus import OperationOutcome
from .finite_probability import FiniteDistribution, distribution_requirements
from .parametric_probability import (
    ParametricDistribution, parametric_requirements, parametric_raw_moment,
    parametric_density, parametric_cdf, parametric_support,
)


def finite_density_call(name, args, assumptions=sp.true):
    if len(args) != 2 or not isinstance(args[0], FiniteDistribution):
        raise ValueError("Use PDF[d,x] o CDF[d,x] con una distribución escalar.")
    distribution, point = args
    if not isinstance(point, sp.Expr) or point.has(sp.nan, sp.zoo):
        raise ValueError("El punto requiere una expresión escalar real.")
    requirements = (*distribution_requirements(distribution, assumptions), sp.Contains(point, sp.S.Reals))
    if point in (sp.oo, -sp.oo):
        requirements = distribution_requirements(distribution, assumptions)
    terms = [sp.Piecewise((mass, sp.Eq(value, point) if name == "PDF" else value <= point), (0, True))
             for value, mass in zip(distribution.states, distribution.probabilities)]
    value = sp.simplify(sp.Add(*terms))
    return OperationOutcome(value, details={"operation": name, "measure": "discrete_probability_mass"}), requirements


def _event_set(event, variable):
    if event is sp.true:
        return sp.S.Reals
    if event is sp.false:
        return sp.S.EmptySet
    if isinstance(event, sp.And):
        return sp.Intersection(*(_event_set(item, variable) for item in event.args))
    if isinstance(event, sp.Or):
        return sp.Union(*(_event_set(item, variable) for item in event.args))
    if isinstance(event, sp.Not):
        return sp.Complement(sp.S.Reals, _event_set(event.args[0], variable))
    if not isinstance(event, Relational):
        raise ValueError("Se requiere un evento lógico univariado.")
    real_parameters = {item: sp.Dummy(item.name, real=True)
                       for item in event.free_symbols-{variable}}
    local = event.xreplace(real_parameters)
    if not local.has(variable):
        raise ValueError("El evento depende de parámetros indecididos; especialícelos.")
    if isinstance(local, sp.Equality):
        result = sp.solveset(local.lhs-local.rhs, variable, domain=sp.S.Reals)
    elif isinstance(local, sp.Unequality):
        result = sp.Complement(sp.S.Reals, sp.solveset(local.lhs-local.rhs, variable, domain=sp.S.Reals))
    else:
        result = sp.solve_univariate_inequality(local, variable, relational=False)
    result = result.xreplace({value: key for key, value in real_parameters.items()})
    if result.has(sp.ConditionSet):
        raise ValueError("No se resolvió el dominio del evento; use desigualdades o intervalos explícitos.")
    return result


def _probability(distribution, domain):
    if domain is sp.S.EmptySet:
        return sp.S.Zero
    if domain == sp.S.Reals:
        return sp.S.One
    if isinstance(domain, sp.Union):
        return sp.Add(*(_probability(distribution, item) for item in domain.args))
    if isinstance(domain, sp.FiniteSet):
        if not distribution.is_discrete:
            return sp.S.Zero
        return sp.Add(*(parametric_density(distribution, point) for point in domain))
    if not isinstance(domain, sp.Interval):
        raise ValueError("El evento debe reducirse a una unión finita de intervalos y puntos.")
    lower, upper = domain.start, domain.end
    if distribution.is_discrete:
        if lower != -sp.oo:
            lower = sp.floor(lower) if domain.left_open else sp.ceiling(lower)-1
        if upper != sp.oo:
            upper = sp.ceiling(upper)-1 if domain.right_open else sp.floor(upper)
    return sp.simplify(parametric_cdf(distribution, upper)-parametric_cdf(distribution, lower))


def _polynomial_expectation(distribution, expression, variable):
    try:
        polynomial = sp.Poly(expression, variable)
    except sp.PolynomialError:
        return None
    if polynomial.degree() > 12:
        raise ValueError("Los observables polinómicos admiten grado hasta doce.")
    return sp.Add(*(coefficient*parametric_raw_moment(distribution, power[0])
                    for power, coefficient in polynomial.terms()))


def _expectation(distribution, expression, variable, domain):
    if distribution.is_discrete:
        support = parametric_support(distribution)
        if isinstance(support, sp.FiniteSet):
            active = sp.Intersection(support, domain)
            if isinstance(active, sp.FiniteSet) or active is sp.S.EmptySet:
                return sp.Add(*(expression.subs(variable, point)*parametric_density(distribution, point)
                                for point in active)), True
    if domain == sp.S.Reals:
        polynomial = _polynomial_expectation(distribution, expression, variable)
        if polynomial is not None:
            return sp.simplify(polynomial), True
    if domain is sp.S.EmptySet:
        return sp.S.Zero, True
    if isinstance(domain, sp.Union):
        parts = [_expectation(distribution, expression, variable, item) for item in domain.args]
        return sp.Add(*(value for value, verified in parts)), all(verified for value, verified in parts)
    if distribution.is_discrete:
        if isinstance(domain, sp.FiniteSet):
            return sp.Add(*(expression.subs(variable, point)*parametric_density(distribution, point)
                            for point in domain)), True
        if not isinstance(domain, sp.Interval) and domain != sp.S.Reals:
            raise ValueError("El dominio discreto debe reducirse a intervalos o puntos.")
        lower = 0 if domain == sp.S.Reals or domain.start == -sp.oo else (
            sp.floor(domain.start)+1 if domain.left_open else sp.ceiling(domain.start))
        upper = sp.oo if domain == sp.S.Reals else (
            sp.ceiling(domain.end)-1 if domain.right_open and domain.end != sp.oo else sp.floor(domain.end))
        if distribution.family == "BinomialDistribution":
            n = distribution.parameters[0]
            upper = sp.Min(n, upper)
        lower = sp.Max(0, lower)
        term = expression*parametric_density(distribution, variable)
        if lower.is_Integer and upper.is_Integer and 0 <= upper-lower <= 63:
            terms = []
            for k in range(int(lower), int(upper)+1):
                mass = sp.simplify(parametric_density(distribution, sp.Integer(k)))
                if mass.is_zero is True:
                    continue
                terms.append(mass*expression.subs(variable, k))
            return sp.simplify(sp.Add(*terms)), True
        pending = sp.Sum(term, (variable, lower, upper))
        return pending, False
    if isinstance(domain, sp.FiniteSet):
        return sp.S.Zero, True
    if domain == sp.S.Reals:
        lower, upper = -sp.oo, sp.oo
    elif isinstance(domain, sp.Interval):
        lower, upper = domain.start, domain.end
    else:
        raise ValueError("El dominio continuo debe reducirse a intervalos.")
    if distribution.family != "NormalDistribution":
        lower = sp.Max(0, lower)
    if sp.simplify(upper-lower).is_nonpositive is True:
        return sp.S.Zero, True
    integrand = expression*parametric_density(distribution, variable)
    pending = sp.Integral(integrand, (variable, lower, upper))
    polynomial = _polynomial_expectation(distribution, expression, variable)
    if polynomial is None:
        absolute = sp.integrate(sp.Abs(expression)*parametric_density(distribution, variable),
                                (variable, lower, upper))
        if absolute.is_finite is False or absolute.has(sp.zoo, sp.nan):
            raise ValueError("El observable no tiene esperanza absolutamente convergente.")
        if absolute.has(sp.Integral, sp.Sum) or absolute.is_finite is not True:
            return pending, False
    value = sp.integrate(integrand, (variable, lower, upper))
    return value, not value.has(sp.Integral, sp.Sum)


def bound_parametric_call(node, distribution, symbols, build, restrictions, state,
                          bindings, functions, definitions, event_node=None):
    from .language_ops import EvaluationState, checked_restrictions
    from .probability_language import absorb_probability

    if len(symbols) != 1:
        raise ValueError("Las familias paramétricas actuales son univariadas.")
    if node.value == "ConditionalDistribution":
        raise ValueError("Para familias paramétricas use Expectation[expr,{x,d},evento]; ConditionalDistribution admite tablas finitas.")
    absorb_probability((OperationOutcome(distribution), parametric_requirements(distribution, state.assumptions)), state)
    input_floats = set(distribution.atoms(sp.Float))
    distribution = distribution.xreplace({item: sp.Rational(item) for item in input_floats})
    name = str(symbols[0])
    variable = sp.Dummy(name, integer=True) if distribution.is_discrete else sp.Dummy(name, real=True)
    local_definitions = {key: value for key, value in definitions.items() if key != name}
    assumptions = sp.And(*(condition for condition in sp.And.make_args(state.assumptions)
                           if symbols[0] not in condition.free_symbols))
    active_domain = sp.S.Reals

    def read(raw):
        child = EvaluationState(assumptions=assumptions, sum_terms=state.sum_terms,
                                call_depth=state.call_depth, steps=state.steps)
        local = []
        value = build(raw, local, child, {**bindings, name: variable}, functions, local_definitions)
        # Cancelled holes are harmless only on sets of probability zero. Keep
        # this check separate from convergence of the simplified observable.
        for excluded in local:
            if not excluded.has(variable):
                continue
            zeros = sp.solveset(excluded, variable, domain=sp.S.Reals)
            zeros = sp.Intersection(zeros, active_domain)
            if zeros.has(sp.ConditionSet):
                raise ValueError("No se pudo comprobar la masa de las singularidades del observable.")
            mass = _probability(distribution, zeros)
            require(sp.Eq(mass, 0))
        restrictions.extend(checked_restrictions([item for item in local if not item.has(variable)]))
        state.steps, state.sum_terms = child.steps, child.sum_terms
        for condition in child.requirements:
            if condition.has(variable):
                raise ValueError("El observable tiene condiciones locales pendientes; especialice antes de promediar.")
        state.requirements.extend(child.requirements)
        state.conditions.extend(child.conditions)
        state.warnings.extend(child.warnings)
        input_floats.update(value.atoms(sp.Float))
        return value.xreplace({item: sp.Rational(item) for item in value.atoms(sp.Float)})

    def require(condition):
        absorb_probability((OperationOutcome(sp.S.Zero), (condition,)), state)

    def event_domain(raw):
        event = read(raw)
        for relation in event.atoms(Relational):
            for operand in (relation.lhs, relation.rhs):
                if not operand.has(variable) and operand not in (sp.oo, -sp.oo):
                    require(sp.Contains(operand, sp.S.Reals))
        return _event_set(event, variable)

    domain = sp.S.Reals if event_node is None else event_domain(event_node)
    active_domain = domain
    if node.value == "Probability":
        value = _probability(distribution, event_domain(node.children[0]))
        verified = not value.has(sp.Sum, sp.Integral)
    else:
        expression = read(node.children[0])
        if not isinstance(expression, sp.Expr) or sp.count_ops(expression) > 256:
            raise ValueError("El observable requiere un escalar con hasta 256 operaciones.")
        if expression.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
            raise ValueError("El observable está indefinido.")
        value, verified = _expectation(distribution, expression, variable, domain)
        if node.value in {"Covariance", "Correlation"}:
            other = read(node.children[1])
            for observable in (expression, other):
                for coefficient in sp.Poly(observable, variable).all_coeffs():
                    require(sp.Contains(coefficient, sp.S.Reals))
            mean_other, ok = _expectation(distribution, other, variable, domain)
            product, ok_product = _expectation(distribution, expression*other, variable, domain)
            covariance = sp.simplify(product-value*mean_other)
            if node.value == "Correlation":
                second, ok_second = _expectation(distribution, expression**2, variable, domain)
                other_second, ok_other = _expectation(distribution, other**2, variable, domain)
                variance = sp.simplify(second-value**2)
                other_variance = sp.simplify(other_second-mean_other**2)
                require(sp.Gt(variance, 0))
                require(sp.Gt(other_variance, 0))
                covariance /= sp.sqrt(variance*other_variance)
                verified = verified and ok_second and ok_other
            value, verified = sp.simplify(covariance), verified and ok and ok_product
        if event_node is not None:
            probability = _probability(distribution, domain)
            require(sp.Gt(probability, 0))
            value = sp.simplify(value/probability)
            verified = verified and not probability.has(sp.Sum, sp.Integral)
    if value.has(sp.zoo, sp.nan) or value.is_finite is False:
        raise ValueError("El resultado probabilístico diverge o está indefinido.")
    if sp.count_ops(value) > 4096:
        raise ValueError("El resultado excede 4096 operaciones.")
    if not verified:
        state.mark_status("unresolved")
        state.warnings.append("La suma, integral o convergencia permanece pendiente; no es un valor numérico certificado.")
    if input_floats:
        digits = max(2, int(min(item._prec for item in input_floats)*0.30103))
        if verified:
            value = value.evalf(digits)
        state.warnings.append("Se opera con los racionales binarios almacenados y se aproxima al final; no se certifica incertidumbre de los datos.")
    state.details.update(operation=node.value, method="univariate_family_measure",
                         measure="discrete_probability_mass" if distribution.is_discrete else "continuous_density",
                         domain_analysis="partial", precision_certified=False,
                         conditional_event=event_node is not None)
    return value


def conditional_expectation_call(node, build, restrictions, state, bindings, functions, definitions):
    from .kernel import Node
    from .language_ops import variable
    from .probability_sampling import bound_probability_call
    from .probability_language import absorb_probability

    observable, specification, event = node.children
    if specification.kind != "list" or len(specification.children) != 2:
        raise ValueError("Use Expectation[expr,{x,d},evento].")
    distribution = build(specification.children[1], restrictions, state, bindings, functions, definitions)
    ordinary = Node("call", "Expectation", (observable, specification))
    if isinstance(distribution, ParametricDistribution):
        symbols = (variable(specification.children[0]),)
        return bound_parametric_call(ordinary, distribution, symbols, build, restrictions, state,
                                     bindings, functions, definitions, event_node=event)
    probability_node = Node("call", "Probability", (event, specification))
    probability = bound_probability_call(probability_node, build, restrictions, state, bindings, functions, definitions)
    absorb_probability((OperationOutcome(sp.S.Zero), (sp.Gt(probability, 0),)), state)
    selected = Node("call", "If", (event, observable, Node("number", "0")))
    numerator_node = Node("call", "Expectation", (selected, specification))
    numerator = bound_probability_call(numerator_node, build, restrictions, state, bindings, functions, definitions)
    return sp.simplify(numerator/probability)
