"""Population moments, transforms and cumulants with bounded exact orders."""

from functools import lru_cache
from itertools import product

import sympy as sp

from .assumptions import combine_assumptions, predicates
from .calculus import OperationOutcome
from .finite_probability import FiniteDistribution, _scalar, distribution_requirements
from .joint_probability import JointFiniteDistribution, joint_requirements
from .parametric_probability import (
    ParametricDistribution, parametric_raw_moment, parametric_requirements,
    parametric_transform,
)

MOMENT_CALLS = frozenset({"MGF", "CF", "Moment", "CentralMoment", "Cumulant"})
MAX_ORDER = 12


def _requirements(conditions, assumptions):
    result = []
    for condition in conditions:
        if condition is sp.false:
            raise ValueError("El cálculo viola una condición de los momentos o de su transformada.")
        try:
            answer = sp.ask(predicates(condition), predicates(assumptions))
        except (ValueError, TypeError, NotImplementedError):
            answer = None
        condition = sp.true if answer is True else sp.false if answer is False else condition
        combine_assumptions(assumptions, condition)
        if condition is not sp.true:
            result.append(condition)
    return tuple(dict.fromkeys(result))


def _distribution(distribution, assumptions):
    if isinstance(distribution, JointFiniteDistribution):
        return distribution.dimension, joint_requirements(distribution, assumptions)
    if isinstance(distribution, FiniteDistribution):
        return 1, distribution_requirements(distribution, assumptions)
    if isinstance(distribution, ParametricDistribution):
        return 1, parametric_requirements(distribution, assumptions)
    raise ValueError("Se requiere una distribución finita, conjunta finita o paramétrica admitida.")


def _orders(raw, dimension, cumulant=False):
    if dimension == 1:
        values = (raw,)
    elif isinstance(raw, (tuple, list, sp.Tuple)) and len(raw) == dimension:
        values = tuple(raw)
    else:
        raise ValueError("Use un multiíndice con un orden por coordenada de la distribución conjunta.")
    values = tuple(sp.Integer(value) if type(value) is int else value for value in values)
    if (any(not isinstance(value, sp.Integer) or value < 0 for value in values)
            or sum(values) > MAX_ORDER or cumulant and sum(values) == 0):
        raise ValueError("Los órdenes deben ser enteros no negativos y sumar hasta doce; un cumulante requiere orden positivo.")
    return tuple(int(value) for value in values)


def _arguments(raw, dimension):
    if dimension == 1:
        values = (_scalar(raw),)
    elif isinstance(raw, (tuple, list, sp.Tuple)) and len(raw) == dimension:
        values = tuple(_scalar(value) for value in raw)
    else:
        raise ValueError("La transformada conjunta requiere un argumento real por coordenada.")
    return values


def _bounded(value):
    if not isinstance(value, sp.Expr) or int(sp.count_ops(value)) > 4096:
        raise ValueError("El resultado de momentos excede 4096 operaciones escalares.")
    if value.has(sp.oo, -sp.oo, sp.zoo, sp.nan) or value.is_finite is False:
        raise ValueError("El momento o la transformada no produce un resultado finito.")
    return value


def _raw_moments(distribution, dimension):
    if isinstance(distribution, ParametricDistribution):
        return lru_cache(None)(lambda orders: _bounded(parametric_raw_moment(distribution, orders[0])))
    rows = distribution.states if dimension > 1 else tuple((state,) for state in distribution.states)
    probabilities = distribution.probabilities

    @lru_cache(None)
    def raw(orders):
        if not any(orders):
            return sp.S.One
        terms = (probability*sp.Mul(*(coordinate**order for coordinate, order in zip(row, orders)))
                 for row, probability in zip(rows, probabilities) if probability.is_zero is not True)
        return _bounded(sp.expand(sp.Add(*terms)))

    return raw


def _central_moment(raw, orders):
    means = tuple(raw(tuple(int(index == coordinate) for index in range(len(orders))))
                  for coordinate in range(len(orders)))
    terms = []
    for powers in product(*(range(order+1) for order in orders)):
        coefficient = sp.Mul(*(sp.binomial(order, power)*(-mean)**(order-power)
                               for order, power, mean in zip(orders, powers, means)))
        terms.append(coefficient*raw(powers))
    return _bounded(sp.expand(sp.Add(*terms)))


def _cumulant(raw, orders):
    @lru_cache(None)
    def cumulant(alpha):
        pivot = next(index for index, order in enumerate(alpha) if order)
        terms = []
        for beta in product(*(range(order+1) for order in alpha)):
            if not beta[pivot] or beta == alpha:
                continue
            coefficient = sp.binomial(alpha[pivot]-1, beta[pivot]-1)
            coefficient *= sp.Mul(*(sp.binomial(order, selected)
                                    for index, (order, selected) in enumerate(zip(alpha, beta))
                                    if index != pivot))
            remainder = tuple(order-selected for order, selected in zip(alpha, beta))
            terms.append(coefficient*cumulant(beta)*raw(remainder))
        # Differentiate M=exp(K) once in the pivot coordinate, then compare
        # coefficients. Choosing the pivot avoids counting that occurrence twice.
        return _bounded(sp.expand(raw(alpha)-sp.Add(*terms)))

    return cumulant(orders)


def _family_cumulant(distribution, order):
    family, parameters = distribution.family, distribution.parameters
    if family == "PoissonDistribution":
        return parameters[0]
    if family == "NormalDistribution":
        return parameters[0] if order == 1 else parameters[1]**2 if order == 2 else sp.S.Zero
    if family == "ExponentialDistribution":
        return sp.factorial(order-1)/parameters[0]**order
    if family == "GammaDistribution":
        shape, scale = parameters
        return shape*sp.factorial(order-1)*scale**order
    trials, probability = parameters
    p = sp.Dummy("p")
    polynomial = p
    for _ in range(1, order):
        polynomial = sp.expand(p*(1-p)*sp.diff(polynomial, p))
    return trials*polynomial.subs(p, probability)


def moment_operation(name, args, assumptions=sp.true):
    """Return (outcome, requirements) for population transforms and moments.

    Scalar orders and sums of joint orders are bounded by twelve. Repeated
    joint transform arguments evaluate the diagonal, without merging coordinates.
    All supported families have moments of every nonnegative integer order.
    """
    if name not in MOMENT_CALLS or len(args) != 2:
        raise ValueError("Use MGF[d,t], CF[d,t], Moment[d,n], CentralMoment[d,n] o Cumulant[d,n].")
    distribution = args[0]
    dimension, requirements = _distribution(distribution, assumptions)
    if (sum(int(sp.count_ops(argument)) for argument in args) > 256
            or len(set().union(*(argument.free_symbols for argument in args if isinstance(argument, sp.Basic)))) > 8):
        raise ValueError("Los argumentos exceden ocho símbolos o 256 operaciones de entrada.")
    floats = set().union(*(argument.atoms(sp.Float) for argument in args if isinstance(argument, sp.Basic)))
    # Exact stored binary inputs avoid catastrophic cancellation when converting
    # large raw moments to small centered moments or cumulants.
    replacements = {value: sp.Rational(value) for value in floats}
    working = distribution.xreplace(replacements)
    warnings = []
    if floats:
        warnings.append("Los momentos usan los valores binarios almacenados como racionales exactos y aproximan al final; no se certifica incertidumbre ni precisión física.")
    extra = ()
    details = {"operation": name, "method": "population_moment_formulas", "dimension": dimension,
               "precision_certified": False, "sympy_version": sp.__version__, "domain_analysis": "partial"}
    if name in {"MGF", "CF"}:
        parameters = _arguments(args[1], dimension)
        parameters = tuple(parameter.xreplace(replacements) for parameter in parameters)
        extra = tuple(sp.Contains(parameter, sp.S.Reals) for parameter in parameters)
        if isinstance(working, ParametricDistribution):
            value, convergence = parametric_transform(working, parameters[0], characteristic=name == "CF")
            extra += tuple(convergence)
        else:
            rows = working.states if dimension > 1 else tuple((state,) for state in working.states)
            factor = sp.I if name == "CF" else sp.S.One
            value = sp.Add(*(probability*sp.exp(factor*sp.Add(*(parameter*coordinate
                            for parameter, coordinate in zip(parameters, row))))
                            for row, probability in zip(rows, working.probabilities)
                            if probability.is_zero is not True))
        details.update(transform="characteristic" if name == "CF" else "moment_generating",
                       characteristic_sign="positive", argument_domain="real")
    else:
        orders = _orders(args[1], dimension, name == "Cumulant")
        raw = _raw_moments(working, dimension)
        if name == "Moment":
            value = raw(orders)
        elif name == "CentralMoment":
            value = _central_moment(raw, orders)
        elif isinstance(working, ParametricDistribution):
            value = _family_cumulant(working, orders[0])
        else:
            value = _cumulant(raw, orders)
        details.update(moment_order=orders[0] if dimension == 1 else list(orders),
                       moment_convention="population_centered" if name == "CentralMoment" else "population_raw"
                       if name == "Moment" else "derivatives_of_log_mgf_at_zero")
    requirements = _requirements((*requirements, *extra), assumptions)
    value = _bounded(sp.simplify(value))
    if floats:
        digits = max(2, int(min(value._prec for value in floats)*0.30103))
        value = _bounded(value.evalf(digits))
    status = "conditional" if requirements else "evaluated"
    return OperationOutcome(value, status, tuple(map(sp.sstr, requirements)), tuple(warnings), details), requirements
