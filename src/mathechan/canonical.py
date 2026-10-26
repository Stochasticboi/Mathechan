"""Finite canonical states with explicit level degeneracies and thermal units.

The state stores validated mathematical data, not executable source. Queries
use a fixed spectrum, with beta=1/(k_B*T), entropy S/k_B and heat capacity C/k_B.
"""

import sympy as sp

from .assumptions import combine_assumptions, predicates
from .calculus import OperationOutcome
from .finite_probability import FiniteDistribution, _scalar

CANONICAL_CALLS = frozenset({
    "Canon", "LogZ", "Dist", "Energy", "FreeEnergy", "HeatCapacity", "Levels", "Degens",
})
CANONICAL_QUERIES = frozenset({
    "Probabilities", "LogZ", "Dist", "Energy", "Variance", "Entropy",
    "FreeEnergy", "HeatCapacity", "Levels", "Degens",
})
MAX_COEFFICIENT_BITS = 12000


def _coefficient_budget(value):
    for coefficient in value.atoms(sp.Rational):
        if max(abs(int(coefficient.p)).bit_length(), int(coefficient.q).bit_length()) > MAX_COEFFICIENT_BITS:
            raise ValueError("Los coeficientes canónicos exceden 12000 bits de representación.")


def _values(raw):
    if not isinstance(raw, (tuple, list, sp.Tuple)) or not 1 <= len(raw) <= 64:
        raise ValueError("Se requiere una lista de uno a 64 niveles.")
    return sp.Tuple(*(_scalar(item) for item in raw))


def _conditions(energies, beta, degeneracies):
    conditions = [sp.Contains(value, sp.S.Reals) for value in energies]
    if beta not in (sp.oo, -sp.oo):
        conditions.append(sp.Contains(beta, sp.S.Reals))
    for value in degeneracies:
        conditions.extend((sp.Contains(value, sp.S.Integers), sp.Gt(value, 0)))
    if any(condition is sp.false for condition in conditions):
        raise ValueError("Las energías y beta deben ser reales; las degeneraciones, enteros positivos.")
    return tuple(dict.fromkeys(condition for condition in conditions if condition is not sp.true))


def _working(state):
    mapping = {value: sp.Rational(value) for value in state.atoms(sp.Float)}
    return state.energies.xreplace(mapping), state.beta.xreplace(mapping), state.degeneracies.xreplace(mapping)


def _extremum(energies, beta):
    if any(energy.free_symbols for energy in energies):
        raise ValueError("Los límites de beta requieren energías numéricas cuyo orden pueda decidirse.")
    chosen = energies[0]
    for energy in energies[1:]:
        difference = sp.simplify(energy-chosen)
        if difference.is_zero is True:
            continue
        closer = difference.is_negative if beta is sp.oo else difference.is_positive
        farther = difference.is_positive if beta is sp.oo else difference.is_negative
        if closer is True:
            chosen = energy
        elif farther is not True:
            raise ValueError("No se pudo decidir exactamente el orden de los niveles para el límite.")
    return chosen


class CanonicalState(sp.Basic):
    """A finite spectrum, signed inverse temperature, multiplicities and precision."""

    def __new__(cls, energies, beta, degeneracies=None, precision=0):
        energies = _values(energies)
        beta = beta if beta in (sp.oo, -sp.oo) else _scalar(beta)
        degeneracies = (sp.Tuple(*(sp.S.One for _ in energies)) if degeneracies is None
                        else _values(degeneracies))
        if len(energies) != len(degeneracies):
            raise ValueError("Cada nivel requiere una degeneración.")
        if type(precision) is int:
            precision = sp.Integer(precision)
        if not isinstance(precision, sp.Integer) or precision != 0 and not 10 <= precision <= 200:
            raise ValueError("La precisión debe ser cero (exacta/automática) o un entero de 10 a 200.")
        entries = (*energies, beta, *degeneracies)
        for item in entries:
            _coefficient_budget(item)
        if (sum(int(sp.count_ops(item)) for item in entries) > 256 or
                len(set().union(*(item.free_symbols for item in entries))) > 8):
            raise ValueError("El sistema canónico excede ocho símbolos o 256 operaciones de entrada.")
        spectrum_symbols = set().union(*(item.free_symbols for item in (*energies, *degeneracies)))
        if beta.free_symbols & spectrum_symbols:
            raise ValueError("Los parámetros de beta deben ser independientes de los niveles y degeneraciones; este modelo requiere un espectro fijo.")
        _conditions(energies, beta, degeneracies)
        if beta in (sp.oo, -sp.oo):
            mapping = {value: sp.Rational(value) for item in energies for value in item.atoms(sp.Float)}
            _extremum(energies.xreplace(mapping), beta)
        if precision and any(item.free_symbols for item in entries):
            raise ValueError("La precisión numérica requiere energías, beta y degeneraciones numéricas.")
        return sp.Basic.__new__(cls, energies, beta, degeneracies, precision)

    @property
    def energies(self):
        return self.args[0]

    @property
    def beta(self):
        return self.args[1]

    @property
    def degeneracies(self):
        return self.args[2]

    @property
    def precision(self):
        return int(self.args[3])

    def _sympystr(self, printer):
        return "Canon[" + ",".join(printer.doprint(item) for item in self.args) + "]"


def canonical_requirements(state, assumptions=sp.true):
    if not isinstance(state, CanonicalState):
        raise ValueError("Se requiere un estado canónico creado con Canon.")
    requirements = []
    for condition in _conditions(state.energies, state.beta, state.degeneracies):
        try:
            answer = sp.ask(predicates(condition), predicates(assumptions))
        except (ValueError, TypeError, NotImplementedError):
            answer = None
        refined = sp.true if answer is True else sp.false if answer is False else condition
        combine_assumptions(assumptions, refined)
        if refined is not sp.true:
            requirements.append(refined)
    return tuple(dict.fromkeys(requirements))


def _exact_values(state):
    energies, beta, degeneracies = _working(state)
    reference = energies[0]
    relative = tuple(sp.simplify(energy-reference) for energy in energies)
    weights = tuple(g*sp.exp(-beta*energy) for g, energy in zip(degeneracies, relative))
    normalizer = sp.Add(*weights)
    probabilities = sp.Tuple(*(sp.cancel(weight/normalizer) for weight in weights))
    mean_relative = sp.simplify(sp.Add(*(p*energy for p, energy in zip(probabilities, relative))))
    variance = sp.simplify(sp.Add(*(p*(energy-mean_relative)**2
                                  for p, energy in zip(probabilities, relative))))
    log_relative = sp.log(normalizer)
    return {
        "probabilities": probabilities,
        "logz": sp.simplify(log_relative-beta*reference),
        "energy": sp.simplify(reference+mean_relative),
        "variance": variance,
        "entropy": sp.simplify(log_relative+beta*mean_relative),
        "free_energy": None if beta.is_zero is True else sp.simplify(reference-log_relative/beta),
        "heat_capacity": sp.simplify(beta**2*variance),
    }


def _limit_values(state):
    energies, beta, degeneracies = _working(state)
    extreme = _extremum(energies, beta)
    selected = tuple(sp.simplify(energy-extreme).is_zero is True for energy in energies)
    total = sp.Add(*(g for g, active in zip(degeneracies, selected) if active))
    probabilities = sp.Tuple(*(sp.cancel(g/total) if active else sp.S.Zero
                               for g, active in zip(degeneracies, selected)))
    if extreme.is_zero is True:
        logz = sp.log(total)
    elif extreme.is_positive is True:
        logz = -sp.oo if beta is sp.oo else sp.oo
    elif extreme.is_negative is True:
        logz = sp.oo if beta is sp.oo else -sp.oo
    else:
        raise ValueError("No se pudo decidir el signo del nivel extremo para la partición límite.")
    return {"probabilities": probabilities, "logz": logz, "energy": extreme,
            "variance": sp.S.Zero, "entropy": sp.log(total), "free_energy": extreme,
            "heat_capacity": sp.S.Zero}


def _numeric_precision(state):
    if state.precision:
        return state.precision
    floats = state.atoms(sp.Float)
    if floats and not state.free_symbols:
        return min(200, max(10, int(min(value._prec for value in floats)*0.30103)))
    return 0


def _bounded(value):
    _coefficient_budget(value)
    if sp.count_ops(value) > 4096:
        raise ValueError("El resultado canónico excede 4096 operaciones.")
    if value.has(sp.zoo, sp.nan) or not isinstance(value, CanonicalState) and value.has(sp.oo, -sp.oo):
        raise ValueError("La consulta canónica no tiene un resultado finito en este límite.")
    return value


def canonical_operation(name, args, assumptions=sp.true):
    """Query finite canonical data; return an outcome and executable requirements."""
    if name == "Canon":
        if not 2 <= len(args) <= 4:
            raise ValueError("Use Canon[energías,beta] con degeneraciones y precisión opcionales.")
        state = CanonicalState(*args)
        value = state
    else:
        if not args or not isinstance(args[0], CanonicalState):
            raise ValueError("La operación requiere un estado creado con Canon.")
        state = args[0]
        if name == "N":
            if len(args) != 2:
                raise ValueError("Use N[estadoCanónico,precisión].")
            state = CanonicalState(state.energies, state.beta, state.degeneracies, args[1])
            value = state
        elif name not in CANONICAL_QUERIES or len(args) != 1:
            raise ValueError("Consulta canónica desconocida o número de argumentos incorrecto.")
        elif name == "Levels":
            value = state.energies
        elif name == "Degens":
            value = state.degeneracies
        else:
            value = None
    requirements = canonical_requirements(state, assumptions)
    details = {"operation": name, "ensemble": "finite_canonical", "levels": len(state.energies),
               "partition_convention": "physical_degeneracy", "entropy_convention": "microstate_S_over_kB",
               "heat_capacity_units": "C_over_kB", "precision_certified": False,
               "state_labels": "one_based_level_groups", "sympy_version": sp.__version__}
    warnings = []
    numeric_precision = _numeric_precision(state)
    if state.has(sp.Float):
        warnings.append("Los datos aproximados se interpretan por sus valores binarios almacenados; no se certifica su incertidumbre física.")
    if value is None:
        if name == "FreeEnergy" and state.beta.is_zero is True:
            raise ValueError("FreeEnergy requiere beta distinto de cero; LogZ y las otras observables sí admiten beta=0.")
        if state.beta in (sp.oo, -sp.oo):
            values = _limit_values(state)
            details.update(method="finite_canonical_limit", beta_limit="positive" if state.beta is sp.oo else "negative")
        elif numeric_precision:
            from .canonical_numeric import canonical_numeric_values
            values = canonical_numeric_values(state.energies, state.beta, state.degeneracies, numeric_precision)
            details.update(values.get("diagnostics", {}))
            details["numeric_method"] = details.get("method")
            details.update(method="finite_canonical_numeric", numeric_ensemble=True,
                           requested_precision=numeric_precision, stored_weight_normalization="exact")
            warnings.append("Las masas internas están normalizadas exactamente como pesos almacenados; esto no certifica las probabilidades físicas ni la precisión numérica.")
        else:
            values = _exact_values(state)
            details.update(method="finite_canonical_exact", numeric_ensemble=False)
        if name == "Dist":
            value = FiniteDistribution(sp.Tuple(*(sp.Integer(index+1) for index in range(len(state.energies)))),
                                       values["probabilities"])
        elif name == "Probabilities":
            value = values["probabilities"]
            if numeric_precision and state.beta not in (sp.oo, -sp.oo):
                value = sp.Tuple(*(probability.evalf(numeric_precision) for probability in value))
        else:
            key = {"LogZ": "logz", "Energy": "energy", "Variance": "variance", "Entropy": "entropy",
                   "FreeEnergy": "free_energy", "HeatCapacity": "heat_capacity"}[name]
            value = values[key]
        if name == "FreeEnergy" and state.beta not in (sp.oo, -sp.oo):
            condition = sp.Ne(state.beta, 0)
            combine_assumptions(assumptions, condition)
            if condition is not sp.true:
                requirements = tuple(dict.fromkeys((*requirements, condition)))
    else:
        details.update(method="canonical_data", requested_precision=numeric_precision)
    value = _bounded(value)
    status = "conditional" if requirements else "approximate" if name == "N" else "evaluated"
    return OperationOutcome(value, status, tuple(map(sp.sstr, requirements)), tuple(warnings), details), requirements
