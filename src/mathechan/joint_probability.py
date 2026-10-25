"""Finite joint masses, coordinate marginals and decided-event conditioning."""

import sympy as sp

from .assumptions import combine_assumptions, predicates
from .finite_probability import (
    FiniteDistribution, MAX_STATES, _scalar, _exact_stored, _result,
    distribution_requirements, probability_operation,
)


def _rows(values):
    if not isinstance(values, (tuple, list, sp.Tuple)) or not 1 <= len(values) <= MAX_STATES:
        raise ValueError("La distribución conjunta requiere entre una y 64 filas.")
    rows = []
    dimension = None
    for row in values:
        if not isinstance(row, (tuple, list, sp.Tuple)) or not 2 <= len(row) <= 4:
            raise ValueError("Cada estado conjunto requiere entre dos y cuatro coordenadas.")
        if dimension is None:
            dimension = len(row)
        if len(row) != dimension:
            raise ValueError("Todos los estados conjuntos deben tener la misma dimensión.")
        rows.append(sp.Tuple(*(_scalar(item) for item in row)))
    return sp.Tuple(*rows)


def _conditions(states, probabilities):
    # Indices form a distinct real state space, so only mass conditions remain.
    proxy = FiniteDistribution(sp.Tuple(*range(len(states))), probabilities)
    conditions = list(distribution_requirements(proxy))
    for row in states:
        conditions.extend(sp.Contains(coordinate, sp.S.Reals) for coordinate in row)
    for index, row in enumerate(states):
        for previous in states[:index]:
            conditions.append(sp.Or(*(sp.Ne(sp.simplify(a-b), 0) for a,b in zip(row, previous))))
    if any(condition is sp.false for condition in conditions):
        raise ValueError("Los estados conjuntos deben ser reales y distintos.")
    return tuple(dict.fromkeys(condition for condition in conditions if condition is not sp.true))


class JointFiniteDistribution(sp.Basic):
    """Immutable rows of real coordinates and one normalized mass per row."""

    def __new__(cls, states, probabilities):
        states = _rows(states)
        if not isinstance(probabilities, (tuple, list, sp.Tuple)) or len(probabilities) != len(states):
            raise ValueError("Estados conjuntos y masas requieren igual longitud.")
        probabilities = sp.Tuple(*(_scalar(item) for item in probabilities))
        entries = tuple(item for row in states for item in row) + tuple(probabilities)
        if (sum(int(sp.count_ops(item)) for item in entries) > 256
                or len(set().union(*(item.free_symbols for item in entries))) > 8):
            raise ValueError("La distribución conjunta excede 256 operaciones u ocho símbolos.")
        _conditions(states, probabilities)
        return sp.Basic.__new__(cls, states, probabilities)

    @property
    def states(self):
        return self.args[0]

    @property
    def probabilities(self):
        return self.args[1]

    @property
    def dimension(self):
        return len(self.states[0])

    def _sympystr(self, printer):
        return "JointFiniteDistribution[" + printer.doprint(self.states) + "," + printer.doprint(self.probabilities) + "]"


def joint_requirements(distribution, assumptions=sp.true):
    """Requirements for a joint distribution, rechecked after specialization."""
    if not isinstance(distribution, JointFiniteDistribution):
        raise ValueError("Se requiere una JointFiniteDistribution.")
    requirements = []
    for condition in _conditions(distribution.states, distribution.probabilities):
        try:
            answer = sp.ask(predicates(condition), predicates(assumptions))
        except (ValueError, TypeError, NotImplementedError):
            answer = None
        condition = sp.true if answer is True else sp.false if answer is False else condition
        combine_assumptions(assumptions, condition)
        if condition is not sp.true:
            requirements.append(condition)
    return tuple(dict.fromkeys(requirements))


def _specialization(assumptions):
    bindings = {}
    for condition in sp.And.make_args(assumptions):
        if isinstance(condition, sp.Equality):
            if isinstance(condition.lhs, sp.Symbol) and not condition.rhs.free_symbols:
                bindings[condition.lhs] = condition.rhs
            elif isinstance(condition.rhs, sp.Symbol) and not condition.lhs.free_symbols:
                bindings[condition.rhs] = condition.lhs
    return bindings


def _stored_masses(distribution):
    """Use exact stored binary values when adding or normalizing Float masses."""
    return tuple(_exact_stored(mass) for mass in distribution.probabilities)


def joint_operation(name, args, assumptions=sp.true):
    """Return (OperationOutcome, requirements) for finite joint operations."""
    if name == "JointFiniteDistribution":
        if len(args) != 2:
            raise ValueError("Use JointFiniteDistribution[estados,masas].")
        value = JointFiniteDistribution(*args)
        requirements = joint_requirements(value, assumptions)
        return _result(value, name, requirements, dimension=value.dimension,
                       states=len(value.states), domain="finite_real_vectors")
    if name == "MarginalDistribution":
        if len(args) != 2 or not isinstance(args[0], JointFiniteDistribution):
            raise ValueError("Use MarginalDistribution[distribuciónConjunta,índiceOLista].")
        distribution, indices = args
        requirements = joint_requirements(distribution, assumptions)
        indices = tuple(indices) if isinstance(indices, (tuple, list, sp.Tuple)) else (indices,)
        if (not indices or any(not isinstance(index, (int, sp.Integer)) or isinstance(index, bool)
                               or not 1 <= int(index) <= distribution.dimension for index in indices)
                or len(set(indices)) != len(indices)):
            raise ValueError("Los índices de marginal deben ser distintos y comenzar en uno.")
        offsets = tuple(int(index)-1 for index in indices)
        bindings = _specialization(assumptions)
        projected, masses = [], []
        for row, mass in zip(distribution.states, _stored_masses(distribution)):
            key = sp.Tuple(*(sp.simplify(row[index].subs(bindings, simultaneous=True)) for index in offsets))
            if key in projected:
                position = projected.index(key)
                masses[position] += mass
            else:
                projected.append(key)
                masses.append(mass)
        if len(offsets) == 1:
            value = FiniteDistribution(sp.Tuple(*(row[0] for row in projected)), sp.Tuple(*masses))
            additional = distribution_requirements(value, assumptions)
        else:
            value = JointFiniteDistribution(sp.Tuple(*projected), sp.Tuple(*masses))
            additional = joint_requirements(value, assumptions)
        requirements = tuple(dict.fromkeys((*requirements, *additional)))
        warnings = ()
        if distribution.has(sp.Float):
            warnings = ("Las masas aproximadas se agregan como sus racionales binarios almacenados; no se certifica incertidumbre de entrada.",)
        return _result(value, name, requirements, warnings, coordinate_indices=list(map(int,indices)),
                       declared_states=len(value.states), domain="finite_coordinate_marginal")
    if len(args) != 1 or not isinstance(args[0], JointFiniteDistribution):
        raise ValueError("La operación requiere una distribución conjunta finita.")
    distribution = args[0]
    requirements = joint_requirements(distribution, assumptions)
    if name == "States":
        value = distribution.states
    elif name == "Probabilities":
        value = distribution.probabilities
    elif name in {"Support", "Entropy"}:
        proxy = FiniteDistribution(sp.Tuple(*range(len(distribution.states))), distribution.probabilities)
        result, additional = probability_operation(name, (proxy,), assumptions)
        value = (sp.Tuple(*(distribution.states[int(index)] for index in result.value))
                 if name == "Support" else result.value)
        requirements = tuple(dict.fromkeys((*requirements, *additional)))
        return _result(value, name, requirements, result.warnings, dimension=distribution.dimension,
                       domain="finite_real_vectors", **({"entropy_units":"nats"} if name == "Entropy" else {}))
    else:
        raise ValueError("Use una marginal o un observable para los momentos de una distribución conjunta.")
    return _result(value, name, requirements, dimension=distribution.dimension, domain="finite_real_vectors")


def condition_distribution(distribution, selection_flags, assumptions=sp.true):
    """Normalize a decided event, retaining its positive mass before cancellation."""
    if isinstance(distribution, JointFiniteDistribution):
        requirements = joint_requirements(distribution, assumptions)
    elif isinstance(distribution, FiniteDistribution):
        requirements = distribution_requirements(distribution, assumptions)
    else:
        raise ValueError("Se requiere una distribución finita o conjunta finita.")
    if (not isinstance(selection_flags, (tuple, list, sp.Tuple))
            or len(selection_flags) != len(distribution.states)
            or any(flag is not True and flag is not False and flag is not sp.true and flag is not sp.false
                   for flag in selection_flags)):
        raise ValueError("El evento debe estar decidido para cada estado declarado.")
    masses = _stored_masses(distribution)
    selected = tuple(mass if flag is True or flag is sp.true else sp.S.Zero
                     for mass,flag in zip(masses,selection_flags))
    total = sp.simplify(sum(selected, sp.S.Zero))
    positive = sp.Gt(total, 0)
    combine_assumptions(sp.And(assumptions, *requirements), positive)
    requirements = tuple(dict.fromkeys((*requirements, *((positive,) if positive is not sp.true else ()))))
    value = distribution.func(distribution.states, sp.Tuple(*(sp.cancel(mass/total) for mass in selected)))
    additional = (joint_requirements(value, assumptions) if isinstance(value,JointFiniteDistribution)
                  else distribution_requirements(value, assumptions))
    requirements = tuple(dict.fromkeys((*requirements, *additional)))
    warnings = []
    if positive is not sp.true:
        warnings.append("La distribución condicionada no conserva por sí sola la condición original P(A)>0; mantenga sus condiciones junto con el resultado.")
    if distribution.has(sp.Float):
        warnings.append("La distribución condicionada usa las masas binarias almacenadas exactas; no se certifica incertidumbre de los datos.")
    return _result(value, "ConditionalDistribution", requirements, warnings,
                   conditioning_probability=sp.sstr(total), event_probability=sp.sstr(total),
                   domain="finite_conditional_probability")
