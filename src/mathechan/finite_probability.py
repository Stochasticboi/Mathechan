"""Finite real probability spaces with executable normalization conditions."""

import sympy as sp

from .calculus import OperationOutcome
from .assumptions import predicates, combine_assumptions

MAX_STATES = 64


def _scalar(value):
    if type(value) is int:
        value = sp.Integer(value)
    if (not isinstance(value, sp.Expr) or value.is_commutative is not True
            or value.has(sp.nan, sp.zoo, sp.oo, -sp.oo) or value.is_finite is False
            or value.is_real is False):
        raise ValueError("Se requieren estados y masas escalares finitos.")
    if any(abs(item._mpf_[2]) > 10000 or item._prec > 4096 for item in value.atoms(sp.Float)):
        raise ValueError("La representación aproximada excede el presupuesto de exponente o precisión.")
    return value


def _tuple(values):
    if not isinstance(values, (list, tuple, sp.Tuple)) or not 1 <= len(values) <= MAX_STATES:
        raise ValueError("Se requiere una lista de entre uno y 64 elementos.")
    return sp.Tuple(*(_scalar(value) for value in values))


def _exact_stored(expression):
    return expression.xreplace({item: sp.Rational(item) for item in expression.atoms(sp.Float)})


def _conditions(states, probabilities):
    conditions = []
    for state in states:
        conditions.append(sp.Contains(state, sp.S.Reals))
    for probability in probabilities:
        conditions.extend((sp.Contains(probability, sp.S.Reals), sp.Ge(probability, 0), sp.Le(probability, 1)))
    for index, state in enumerate(states):
        for previous in states[:index]:
            conditions.append(sp.Ne(sp.simplify(state-previous), 0))
    total = sp.simplify(sum((_exact_stored(p) for p in probabilities), sp.S.Zero))
    conditions.append(sp.Eq(total, 1))
    if any(condition is sp.false for condition in conditions):
        raise ValueError("Los estados deben ser reales y distintos; las masas deben ser no negativas y sumar exactamente uno.")
    return tuple(dict.fromkeys(condition for condition in conditions if condition is not sp.true))


class FiniteDistribution(sp.Basic):
    """Immutable declared states and normalized masses, without executable source."""

    def __new__(cls, states, probabilities):
        states, probabilities = _tuple(states), _tuple(probabilities)
        if len(states) != len(probabilities):
            raise ValueError("Estados y masas deben tener la misma longitud.")
        if (sum(int(sp.count_ops(item)) for item in (*states, *probabilities)) > 256
                or len(set().union(*(item.free_symbols for item in (*states, *probabilities)))) > 8):
            raise ValueError("La distribución excede 256 operaciones u ocho símbolos.")
        _conditions(states, probabilities)
        return sp.Basic.__new__(cls, states, probabilities)

    @property
    def states(self):
        return self.args[0]

    @property
    def probabilities(self):
        return self.args[1]

    def _sympystr(self, printer):
        return "FiniteDistribution[" + printer.doprint(self.states) + "," + printer.doprint(self.probabilities) + "]"


def distribution_requirements(distribution, assumptions=sp.true):
    """Recheck requirements after replacement and under current assumptions."""
    if not isinstance(distribution, FiniteDistribution):
        raise ValueError("Se requiere una FiniteDistribution.")
    conditions = _conditions(distribution.states, distribution.probabilities)
    result = []
    for condition in conditions:
        try:
            answer = sp.ask(predicates(condition), predicates(assumptions))
        except (ValueError, TypeError, NotImplementedError):
            answer = None
        refined = sp.true if answer is True else sp.false if answer is False else condition
        combine_assumptions(assumptions, refined)
        if refined is not sp.true:
            result.append(refined)
    return tuple(dict.fromkeys(result))


def _result(value, operation, requirements=(), warnings=(), **details):
    if sp.count_ops(value) > 4096:
        raise ValueError("El resultado excede 4096 operaciones.")
    return OperationOutcome(value, "conditional" if requirements else "evaluated",
                            tuple(map(sp.sstr, requirements)), tuple(warnings),
                            {"operation": operation, "method": "finite_probability_sum",
                             "domain": "finite_real_states", "sympy_version": sp.__version__,
                             **details}), tuple(requirements)


def probability_operation(name, args, assumptions=sp.true):
    """Evaluate one bounded discrete operation and return real requirements."""
    warnings = []
    requirements = ()
    if name in ("FiniteDistribution", "WeightedDistribution"):
        if len(args) != 2:
            raise ValueError("Use FiniteDistribution[estados,masas] o WeightedDistribution[estados,pesos].")
        if name == "FiniteDistribution":
            value = FiniteDistribution(*args)
        else:
            states, weights = _tuple(args[0]), _tuple(args[1])
            if len(states) != len(weights):
                raise ValueError("Estados y pesos deben tener la misma longitud.")
            total = sp.simplify(sum(weights, sp.S.Zero))
            conditions = [sp.Contains(weight, sp.S.Reals) for weight in weights]
            conditions.extend(sp.Ge(weight, 0) for weight in weights)
            conditions.append(sp.Gt(total, 0))
            if any(condition is sp.false for condition in conditions):
                raise ValueError("Los pesos deben ser reales no negativos y su suma positiva.")
            if any(weight.has(sp.Float) for weight in weights):
                weights = sp.Tuple(*(_exact_stored(weight) for weight in weights))
                total = sp.simplify(sum(weights, sp.S.Zero))
                warnings.append("Los pesos aproximados se normalizan como sus valores binarios almacenados exactos; la incertidumbre de los datos no está certificada.")
            value = FiniteDistribution(states, sp.Tuple(*(sp.cancel(weight/total) for weight in weights)))
            requirements = tuple(condition for condition in conditions if condition is not sp.true)
        requirements = tuple(dict.fromkeys((*requirements, *distribution_requirements(value, assumptions))))
        combine_assumptions(assumptions, sp.And(*requirements))
        if name == "WeightedDistribution" and requirements:
            warnings.append("La distribución normalizada no conserva por sí sola las restricciones de los pesos originales; mantenga sus condiciones junto con el resultado.")
        return _result(value, name, requirements, warnings, states=len(value.states), normalized=True)
    if name == "BernoulliDistribution":
        if len(args) != 1:
            raise ValueError("Use BernoulliDistribution[p].")
        p = _scalar(args[0])
        return probability_operation("FiniteDistribution", (sp.Tuple(0,1), sp.Tuple(1-p,p)), assumptions)
    if name == "DiscreteUniformDistribution":
        if (len(args) != 1 or not isinstance(args[0], (tuple, list, sp.Tuple))
                or len(args[0]) != 2 or any(not isinstance(item, sp.Integer) for item in args[0])):
            raise ValueError("Use DiscreteUniformDistribution[{a,b}] con extremos enteros exactos.")
        lower, upper = map(int, args[0])
        count = upper-lower+1
        if not 1 <= count <= MAX_STATES:
            raise ValueError("El intervalo uniforme requiere entre uno y 64 enteros.")
        return probability_operation("FiniteDistribution", (sp.Tuple(*map(sp.Integer,range(lower,upper+1))),
                                      sp.Tuple(*([sp.Rational(1,count)]*count))), assumptions)
    if len(args) != 1:
        raise ValueError("La operación requiere exactamente una distribución finita.")
    distribution = args[0]
    requirements = distribution_requirements(distribution, assumptions)
    states, probabilities = distribution.states, distribution.probabilities
    if name == "Support":
        support = []
        context = sp.And(assumptions, *requirements)
        bindings = {}
        for condition in sp.And.make_args(assumptions):
            if isinstance(condition, sp.Equality):
                if isinstance(condition.lhs, sp.Symbol) and not condition.rhs.free_symbols:
                    bindings[condition.lhs] = condition.rhs
                elif isinstance(condition.rhs, sp.Symbol) and not condition.lhs.free_symbols:
                    bindings[condition.rhs] = condition.lhs
        for state, probability in zip(states, probabilities):
            sampled = sp.simplify(probability.subs(bindings, simultaneous=True))
            zero = sp.ask(sp.Q.zero(sampled), predicates(context))
            if zero is True:
                continue
            positive = sp.ask(sp.Q.positive(sampled), predicates(context))
            if positive is not True:
                try:
                    combine_assumptions(context, sp.Le(probability, 0))
                except ValueError:
                    positive = True
            if positive is not True:
                raise ValueError("El soporte depende de masas simbólicas nulas; especialice los parámetros.")
            support.append(state)
        value = sp.Tuple(*support)
    elif name == "States":
        value = states
    elif name == "Probabilities":
        value = probabilities
    elif name == "Mean":
        value = sp.simplify(sum((p*x for x,p in zip(states,probabilities)), sp.S.Zero))
    elif name in ("Variance", "StandardDeviation"):
        mean = sum((p*x for x,p in zip(states,probabilities)), sp.S.Zero)
        value = sp.simplify(sum((p*(x-mean)**2 for x,p in zip(states,probabilities)), sp.S.Zero))
        if name == "StandardDeviation":
            value = sp.sqrt(value)
    elif name == "Entropy":
        terms = []
        for probability in probabilities:
            if probability.is_zero is True:
                continue
            term = -probability*sp.log(probability)
            if probability.is_positive is not True:
                term = sp.Piecewise((0,sp.Eq(probability,0)),(term,True))
            terms.append(term)
        value = sp.simplify(sum(terms, sp.S.Zero))
    else:
        raise ValueError("Operación de probabilidad finita desconocida.")
    return _result(value, name, requirements, states=len(states),
                   **({"entropy_units": "nats", "zero_mass_convention": "0*log(0)=0"} if name == "Entropy" else {}))
