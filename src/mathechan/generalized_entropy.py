"""Finite Shannon extensions with explicit support and order conventions."""

import sympy as sp
from sympy.core.evalf import prec_to_dps

from .assumptions import combine_assumptions, predicates
from .calculus import OperationOutcome
from .finite_probability import FiniteDistribution, _exact_stored, _scalar, distribution_requirements
from .joint_probability import JointFiniteDistribution, joint_requirements


ENTROPY_CALLS = frozenset({"Renyi", "Tsallis", "KL", "Escort"})


def _distribution(value, assumptions):
    if isinstance(value, FiniteDistribution):
        return distribution_requirements(value, assumptions)
    if isinstance(value, JointFiniteDistribution):
        return joint_requirements(value, assumptions)
    raise ValueError("Use una distribución finita; convierta modelos con Dist antes de calcular el funcional.")


def _ask(condition, context):
    if condition in (sp.true, sp.false):
        return condition is sp.true
    try:
        return sp.ask(predicates(condition), predicates(context))
    except (ValueError, TypeError, NotImplementedError):
        return None


def _require(condition, assumptions, requirements):
    answer = _ask(condition, sp.And(assumptions, *requirements))
    if answer is False:
        raise ValueError("El orden de la entropía no cumple su dominio real permitido.")
    combine_assumptions(assumptions, condition)
    if answer is not True:
        requirements.append(condition)


def _parameter(value, allow_infinity=False):
    value = sp.sympify(value)
    if allow_infinity and value is sp.oo:
        return value
    value = _scalar(value)
    if sp.count_ops(value) > 64 or len(value.free_symbols) > 4:
        raise ValueError("El orden excede 64 operaciones o cuatro parámetros.")
    if any(max(abs(int(atom.p)).bit_length(), int(atom.q).bit_length()) > 4096
           for atom in value.atoms(sp.Rational)):
        raise ValueError("El orden excede 4096 bits por coeficiente.")
    return value


def _shannon(masses):
    terms = []
    for p in masses:
        if p.is_zero is True:
            continue
        term = -p*sp.log(p)
        if p.is_positive is not True:
            term = sp.Piecewise((0, sp.Eq(p, 0)), (term, True))
        terms.append(term)
    return sp.Add(*terms)


def _support_entropy(masses):
    count = sp.Add(*(sp.S.One if p.is_positive is True else
                     sp.Piecewise((0, sp.Eq(p, 0)), (1, True))
                     for p in masses if p.is_zero is not True))
    return sp.log(count)


def _power(base, order, approximate):
    if base in (0, 1):
        return base
    if order.is_number:
        magnitude = abs(order)
        if magnitude > 12000:
            raise ValueError("La potencia excede el presupuesto conservador de 12000 bits estimados.")
        bits = max((max(abs(int(atom.p)).bit_length(), int(atom.q).bit_length())
                    for atom in base.atoms(sp.Rational)), default=1)
        if bits*int(sp.ceiling(magnitude)) > 12000:
            raise ValueError("La potencia excede el presupuesto conservador de 12000 bits estimados.")
    if approximate:
        return sp.Pow(base, order, evaluate=False)
    return base**order


def _entropic_value(name, masses, order, approximate):
    shannon = _shannon(masses)
    if order == 1:
        return shannon
    if name == "Renyi" and order == 0:
        return _support_entropy(masses)
    if name == "Renyi" and order is sp.oo:
        return -sp.log(sp.Max(*masses))
    total = sp.Add(*(_power(p, order, approximate) for p in masses if p.is_zero is not True))
    value = sp.log(total)/(1-order) if name == "Renyi" else (1-total)/(order-1)
    if order.free_symbols:
        branches = [(shannon, sp.Eq(order, 1))]
        if name == "Renyi":
            branches.insert(0, (_support_entropy(masses), sp.Eq(order, 0)))
        return sp.Piecewise(*branches, (value, True))
    return value


def _precision(arguments):
    floats = set().union(*(sp.sympify(value).atoms(sp.Float) for value in arguments))
    if not floats:
        return None
    return min(100, max(1, min(prec_to_dps(value._prec) for value in floats)))


def _numeric(expression, digits, order=None):
    guard = 30
    if order is not None and not order.free_symbols and order not in (sp.oo, 1):
        distance = abs(order-1)
        if distance.is_positive is True and distance < 1:
            guard += max(0, int(sp.ceiling(-sp.log(distance, 10)).evalf(20)))
    if digits+guard > 600:
        raise ValueError("La cercanía al orden uno excede 600 cifras de trabajo.")
    value = expression.evalf(digits+guard, maxn=3*(digits+guard)).evalf(digits)
    if value.is_real is not True or value.is_finite is not True:
        raise ValueError("La evaluación numérica de la entropía no produjo un valor real finito.")
    if any(abs(atom._mpf_[2]) > 10000 or atom._prec > 4096 for atom in value.atoms(sp.Float)):
        raise ValueError("La entropía aproximada excede el presupuesto de exponente o precisión.")
    return value


def _labels_equal(left, right, context):
    if isinstance(left, sp.Tuple) != isinstance(right, sp.Tuple):
        return False
    if isinstance(left, sp.Tuple):
        if len(left) != len(right):
            return False
        answers = [_ask(sp.Eq(a, b), context) for a, b in zip(left, right)]
        if False in answers:
            return False
        return True if all(answer is True for answer in answers) else None
    return _ask(sp.Eq(left, right), context)


def _relative(first, second, masses, reference, context):
    if type(first) is not type(second) or (
            isinstance(first, JointFiniteDistribution) and first.dimension != second.dimension):
        raise ValueError("KL requiere espacios de estados de la misma clase y dimensión.")
    terms = []
    for label, p in zip(first.states, masses):
        if _ask(sp.Eq(p, 0), context) is True:
            continue
        matches = []
        for index, other in enumerate(second.states):
            match = _labels_equal(label, other, context)
            if match is None:
                raise ValueError("La igualdad de etiquetas de KL es indecidible; especialice los estados.")
            if match:
                matches.append(index)
        if len(matches) > 1:
            raise ValueError("Las etiquetas de KL no identifican estados distintos.")
        q = reference[matches[0]] if matches else sp.S.Zero
        if p == q:
            continue
        if _ask(sp.Eq(q, 0), context) is True:
            if _ask(sp.Gt(p, 0), context) is True:
                return sp.oo
            term = sp.Piecewise((0, sp.Eq(p, 0)), (sp.oo, True))
        else:
            term = p*sp.log(p/q)
            branches = []
            if _ask(sp.Eq(p, 0), context) is not False:
                branches.append((0, sp.Eq(p, 0)))
            if _ask(sp.Gt(q, 0), context) is not True:
                branches.append((sp.oo, sp.Eq(q, 0)))
            if branches:
                term = sp.Piecewise(*branches, (term, True))
        terms.append(term)
    return sp.Add(*terms)


def entropy_operation(name, args, assumptions=sp.true):
    """Return a finite functional or escort distribution and inherited conditions."""
    if name not in ENTROPY_CALLS or len(args) != 2:
        raise ValueError("Use Renyi[d,a], Tsallis[d,q], KL[p,q] o Escort[d,q].")
    distribution = args[0]
    digits = _precision(args)
    approximate = digits is not None
    requirements = list(_distribution(distribution, assumptions))
    masses = tuple(_exact_stored(p) for p in distribution.probabilities)
    order = None
    details = {"operation": name, "domain": "finite_probabilities",
               "method": "finite_entropy_functional", "precision_certified": False}
    if name != "Escort":
        details["entropy_units"] = "dimensionless_Sq_over_kB" if name == "Tsallis" else "nats"
    if name == "KL":
        reference = args[1]
        requirements.extend(_distribution(reference, assumptions))
        other_masses = tuple(_exact_stored(p) for p in reference.probabilities)
        context = sp.And(assumptions, *requirements)
        value = _relative(distribution, reference, masses, other_masses, context)
        details.update(direction="first_relative_to_second", state_alignment="labels",
                       zero_mass_convention="zero_first_mass_contributes_zero")
    else:
        order = _parameter(args[1], allow_infinity=name == "Renyi")
        if order is not sp.oo:
            _require(sp.Contains(order, sp.S.Reals), assumptions, requirements)
            _require(sp.Ge(order, 0) if name == "Renyi" else sp.Gt(order, 0), assumptions, requirements)
        order = _exact_stored(order)
        if name == "Escort":
            weights = tuple(_power(p, order, approximate) if p.is_zero is not True else sp.S.Zero for p in masses)
            normalizer = sp.Add(*weights)
            _require(sp.Gt(normalizer, 0), assumptions, requirements)
            if digits and not normalizer.free_symbols:
                # Rounded positive weights are normalized as exact stored numbers.
                weights = tuple(sp.Rational(_numeric(p, digits+20)) if p else sp.S.Zero for p in weights)
                normalizer = sp.Add(*weights)
            probabilities = sp.Tuple(*(sp.cancel(p/normalizer) for p in weights))
            value = type(distribution)(distribution.states, probabilities)
            requirements.extend(_distribution(value, assumptions))
            details.update(normalized=True, means_convention="explicit_escort_distribution")
        else:
            value = _entropic_value(name, masses, order, approximate)
            details["order"] = sp.sstr(order)
    warnings = []
    if approximate:
        warnings.append("Se usan los valores binarios almacenados de los datos aproximados; las cifras no son cotas certificadas ni incertidumbre experimental.")
        if name != "Escort" and not value.free_symbols and value is not sp.oo:
            value = _numeric(value, digits, order)
    if value.has(sp.nan, sp.zoo, -sp.oo) or sp.count_ops(value) > 4096:
        raise ValueError("El funcional excede su presupuesto o contiene valores indefinidos.")
    if any(max(abs(int(atom.p)).bit_length(), int(atom.q).bit_length()) > 12000
           for atom in value.atoms(sp.Rational)):
        raise ValueError("El funcional excede 12000 bits por coeficiente de salida.")
    requirements = tuple(dict.fromkeys(requirements))
    details.update(input_approximate=approximate, requested_significant_digits=digits,
                   declared_states=len(distribution.states))
    return OperationOutcome(value, "conditional" if requirements else "approximate" if approximate else "evaluated",
                            tuple(map(sp.sstr, requirements)), tuple(warnings), details), requirements
