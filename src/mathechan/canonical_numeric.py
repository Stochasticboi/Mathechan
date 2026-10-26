"""Shifted finite canonical weights with exact binary normalization.

The shift avoids overflow in exponentials (Blanchard, Higham and Higham,
arXiv:1909.03469). Exact normalization of rounded weights is an arithmetic
property, not certification of the physical inputs or of correct digits.
"""

import math

import sympy as sp


MAX_LOG_WEIGHT_SPREAD = 6000
MAX_INPUT_BITS = 16384
MAX_WEIGHT_BITS = 12000


def _number(value):
    if type(value) is int:
        value = sp.Integer(value)
    if (not isinstance(value, sp.Expr) or value.free_symbols or value.is_real is not True
            or value.is_finite is not True or sp.count_ops(value) > 256):
        raise ValueError("El cálculo canónico numérico requiere escalares reales finitos conocidos.")
    for item in value.atoms(sp.Float):
        if abs(item._mpf_[2]) > 10000 or item._prec > 4096:
            raise ValueError("Los datos aproximados exceden el presupuesto de exponente o precisión.")
    value = value.xreplace({item: sp.Rational(item) for item in value.atoms(sp.Float)})
    for item in value.atoms(sp.Rational):
        if max(abs(int(item.p)).bit_length(), int(item.q).bit_length()) > MAX_INPUT_BITS:
            raise ValueError("Los coeficientes canónicos numéricos exceden 16384 bits.")
    return value


def _evaluate(expression, precision, maximum):
    # A rational probability can differ from one only hundreds of decimal
    # places later. Evaluate log(p) at the cancellation budget first; merely
    # passing maxn with a small target can return an inaccurate tiny value.
    value = expression.evalf(maximum, maxn=maximum*2).evalf(precision)
    if value.is_real is not True or value.is_finite is not True or value.has(sp.nan, sp.zoo):
        raise ValueError("La evaluación canónica no produjo un escalar real finito.")
    return value


def canonical_numeric_values(energies, beta, degeneracies, precision):
    """Return finite canonical observables, with no implicit zero tolerance.

    Probabilities are exact rationals normalized from rounded positive weights;
    all other numerical outputs are rounded once at the requested precision.
    Finite beta is required. Endpoint limits are handled by the exact backend.
    Cost is linear in the number of levels, apart from scalar evaluations.
    """
    if type(precision) is int:
        precision = sp.Integer(precision)
    if not isinstance(precision, sp.Integer) or not 10 <= precision <= 200:
        raise ValueError("La precisión debe ser un entero exacto entre diez y doscientas cifras.")
    precision = int(precision)
    if (not isinstance(energies, (tuple, list, sp.Tuple))
            or not isinstance(degeneracies, (tuple, list, sp.Tuple))
            or not 1 <= len(energies) <= 64 or len(energies) != len(degeneracies)):
        raise ValueError("Se requieren entre uno y 64 niveles y una degeneración por nivel.")
    energies = tuple(_number(item) for item in energies)
    beta = _number(beta)
    degeneracies = tuple(sp.Integer(item) if type(item) is int else item for item in degeneracies)
    if any(not isinstance(item, sp.Integer) or item <= 0 for item in degeneracies):
        raise ValueError("Las degeneraciones deben ser enteros exactos estrictamente positivos.")
    degeneracies = tuple(_number(item) for item in degeneracies)
    if sum(int(sp.count_ops(item)) for item in (*energies, beta, *degeneracies)) > 256:
        raise ValueError("Los datos canónicos exceden 256 operaciones.")

    reference = energies[0]
    differences = tuple(sp.simplify(item-reference) for item in energies)
    working = precision+25
    logits = tuple(sp.log(count)-beta*delta for count, delta in zip(degeneracies, differences))
    evaluated_logits = tuple(_evaluate(item, working, working*2) for item in logits)
    largest, smallest = max(evaluated_logits), min(evaluated_logits)
    spread = largest-smallest
    if spread > MAX_LOG_WEIGHT_SPREAD:
        raise ValueError("La dispersión de log-pesos excede 6000; no se descartan probabilidades pequeñas.")
    maximum = max(working*2, working+math.ceil(float(spread)/math.log(10))+50)

    if beta.is_zero is True or all(delta.is_zero is True for delta in differences):
        # These weights are already exact. In particular beta=0 must retain
        # degeneracy counts rather than round an exp(log(g)) calculation.
        weights = degeneracies
        shift = sp.S.Zero
    else:
        shift = sp.Rational(largest)
        rounded = tuple(_evaluate(sp.exp(logit-shift), working, maximum) for logit in logits)
        if any(weight.is_positive is not True for weight in rounded):
            raise ValueError("Un peso numérico perdió positividad; no se reemplaza por cero.")
        if any(abs(weight._mpf_[2])+weight._mpf_[3] > MAX_WEIGHT_BITS
               for weight in rounded if isinstance(weight, sp.Float)):
            raise ValueError("Los pesos canónicos exceden el presupuesto de 12000 bits.")
        weights = tuple(sp.Rational(weight) for weight in rounded)
    normalizer = sp.Add(*weights)
    probabilities = sp.Tuple(*(weight/normalizer for weight in weights))
    if any(max(abs(int(value.p)).bit_length(), int(value.q).bit_length()) > MAX_WEIGHT_BITS
           for value in probabilities):
        raise ValueError("Las probabilidades canónicas exceden el presupuesto de 12000 bits.")
    if sp.Add(*probabilities) != 1 or any(value <= 0 for value in probabilities):
        raise ValueError("No se obtuvo una normalización positiva exacta.")

    relative_mean = sp.Add(*(probability*delta for probability, delta in zip(probabilities, differences)))
    variance_expression = sp.Add(*(probability*(delta-relative_mean)**2
                                   for probability, delta in zip(probabilities, differences)))
    entropy_expression = -sp.Add(*(probability*sp.log(probability/count)
                                  for probability, count in zip(probabilities, degeneracies)))
    # With exact degeneracy weights the shift is zero but the reference-energy
    # factor still belongs to the physical partition function.
    relative_log_partition = shift+sp.log(normalizer)
    log_partition_expression = -beta*reference+relative_log_partition
    canonical_residual = entropy_expression-relative_log_partition-beta*relative_mean

    result = {
        "probabilities": probabilities,
        "logz": _evaluate(log_partition_expression, precision, maximum),
        "energy": _evaluate(reference+relative_mean, precision, maximum),
        "variance": _evaluate(variance_expression, precision, maximum),
        "entropy": _evaluate(entropy_expression, precision, maximum),
        "free_energy": None if beta.is_zero is True else
            _evaluate(reference-relative_log_partition/beta, precision, maximum),
        "heat_capacity": _evaluate(beta**2*variance_expression, precision, maximum),
        "diagnostics": {
            "method": "shifted_logsumexp_exact_binary_normalization",
            "probability_representation": "normalized_rational_weights",
            "normalization_residual": "0",
            "canonical_relation_residual": str(_evaluate(canonical_residual, precision, maximum)),
            "working_precision": working,
            "output_precision": precision,
            "absolute_zero_tolerance": "0",
            "relative_zero_tolerance": "0",
            "precision_certified": False,
        },
    }
    return result
