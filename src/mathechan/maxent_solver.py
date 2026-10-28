"""Finite relative-entropy inference on an exactly identified feasible face."""

import sympy as sp


MAX_ITERATIONS = 200
MAX_WEIGHT_BITS = 12000
METHODS = frozenset({"exact_face_prior", "exact_unique", "exact_two_groups", "damped_newton"})


def _coefficient_budget(values):
    for expression in values:
        if any(max(abs(int(value.p)).bit_length(), int(value.q).bit_length()) > MAX_WEIGHT_BITS
               for value in expression.atoms(sp.Rational)):
            raise ValueError("Los coeficientes del resultado MaxEnt exceden 12000 bits.")


def _precision(value):
    if type(value) is int:
        value = sp.Integer(value)
    if not isinstance(value, sp.Integer) or not 10 <= value <= 100:
        raise ValueError("La precisión de MaxEnt debe ser un entero de diez a cien cifras.")
    return int(value)


def _evaluate(expression, digits):
    value = expression.evalf(digits, maxn=digits*3)
    if value.is_real is not True or value.is_finite is not True:
        raise ValueError("La inferencia MaxEnt no produjo valores reales finitos.")
    return value


def _full_probabilities(active, support, count):
    lookup = dict(zip(support, active))
    result = sp.Tuple(*(lookup.get(index, sp.S.Zero) for index in range(count)))
    if any(not isinstance(value, sp.Rational) or value < 0 for value in result):
        raise ValueError("Las probabilidades deben ser racionales no negativos.")
    if sp.Add(*result) != 1 or any(result[index] <= 0 for index in support):
        raise ValueError("No se obtuvo normalización positiva exacta sobre el soporte activo.")
    if any(max(abs(int(value.p)).bit_length(), int(value.q).bit_length()) > MAX_WEIGHT_BITS for value in result):
        raise ValueError("Las probabilidades MaxEnt exceden 12000 bits por coeficiente.")
    return result


def _exact_dual(features, reference, probabilities, support, basis):
    if not basis:
        return sp.Tuple(*(sp.S.Zero for _ in features[0]))
    first = support[0]
    independent_rows = []
    rhs = []
    for index in support[1:]:
        row = [features[index][column]-features[first][column] for column in basis]
        trial = sp.Matrix([*independent_rows, row])
        if trial.rank() > len(independent_rows):
            independent_rows.append(row)
            rhs.append(-sp.log(probabilities[index]/reference[index])
                       + sp.log(probabilities[first]/reference[first]))
        if len(independent_rows) == len(basis):
            break
    selected = sp.Matrix(independent_rows).inv()*sp.Matrix(rhs)
    lookup = dict(zip(basis, selected))
    return sp.Tuple(*(sp.expand_log(lookup.get(column, sp.S.Zero), force=True)
                      for column in range(len(features[0]))))


def _exact_solution(features, targets, reference, support, basis, feasible):
    total_reference = sp.Add(*(reference[index] for index in support))
    prior = sp.Tuple(*(reference[index]/total_reference for index in support))
    prior_full = _full_probabilities(prior, support, len(features))
    if not basis or all(sp.Add(*(prior_full[index]*features[index][column] for index in support)) == target
                        for column, target in enumerate(targets)):
        return prior_full, "exact_face_prior"
    if len(basis) == len(support)-1:
        return _full_probabilities(tuple(feasible[index] for index in support), support, len(features)), "exact_unique"
    if len(basis) == 1:
        column = basis[0]
        values = sorted({features[index][column] for index in support})
        if len(values) == 2:
            low, high = values
            high_mass = (targets[column]-low)/(high-low)
            masses = {low: 1-high_mass, high: high_mass}
            references = {value: sp.Add(*(reference[index] for index in support
                                         if features[index][column] == value)) for value in values}
            active = tuple(masses[features[index][column]]*reference[index]/references[features[index][column]]
                           for index in support)
            return _full_probabilities(active, support, len(features)), "exact_two_groups"
    return None


def _newton(features, targets, reference, support, basis, precision, feasible):
    smallest_witness = min(feasible[index] for index in support)
    extra_digits = max(0, int(sp.ceiling(-sp.log(smallest_witness, 10)).evalf(20)))
    working = precision+40+extra_digits
    if working > 2000:
        raise ValueError("La cercanía a la frontera excede 2000 cifras de trabajo; no se declara convergencia.")
    rank = len(basis)
    first = support[0]
    offsets = tuple(features[first][column] for column in basis)
    scales = tuple(max(abs(features[index][column]-offset) for index in support)
                   for column, offset in zip(basis, offsets))
    rows = tuple(tuple((features[index][column]-offset)/scale
                       for column, offset, scale in zip(basis, offsets, scales)) for index in support)
    desired = tuple((targets[column]-offset)/scale for column, offset, scale in zip(basis, offsets, scales))
    numerical_rows = tuple(tuple(_evaluate(value, working) for value in row) for row in rows)
    numerical_targets = sp.Matrix([_evaluate(value, working) for value in desired])
    log_reference = tuple(_evaluate(sp.log(reference[index]), working) for index in support)
    theta = sp.zeros(rank, 1)
    tolerance = sp.Float(10, working)**(-precision-10)*smallest_witness
    rounding = sp.Float(10, working)**(-working+10)

    def state(parameter):
        logits = tuple(logq-sp.Add(*(value*coefficient for value, coefficient in zip(row, parameter)))
                       for logq, row in zip(log_reference, numerical_rows))
        shift = max(logits)
        if shift-min(logits) > 6000:
            raise ValueError("La dispersión de log-pesos MaxEnt excede 6000; no se eliminan colas.")
        weights = tuple(_evaluate(sp.exp(logit-shift), working) for logit in logits)
        if any(value <= 0 for value in weights):
            raise ValueError("Un peso numérico perdió positividad; no se reemplaza por cero.")
        normalizer = sp.Add(*weights)
        probabilities = tuple(value/normalizer for value in weights)
        mean = sp.Matrix([sp.Add(*(p*row[column] for p, row in zip(probabilities, numerical_rows)))
                          for column in range(rank)])
        gradient = numerical_targets-mean
        covariance = sp.Matrix(rank, rank, lambda i, j: sp.Add(*(
            p*(row[i]-mean[i])*(row[j]-mean[j]) for p, row in zip(probabilities, numerical_rows))))
        objective = shift+sp.log(normalizer)+(parameter.T*numerical_targets)[0]
        return weights, gradient, covariance, objective

    current = state(theta)
    for iteration in range(MAX_ITERATIONS+1):
        weights, gradient, covariance, objective = current
        error = max(abs(value) for value in gradient)
        if error <= tolerance:
            rounded = tuple(_evaluate(value, precision+25) for value in weights)
            if any(abs(value._mpf_[2])+value._mpf_[3] > MAX_WEIGHT_BITS for value in rounded):
                raise ValueError("Los pesos MaxEnt exceden 12000 bits.")
            rational_weights = tuple(sp.Rational(value) for value in rounded)
            normalizer = sp.Add(*rational_weights)
            p = _full_probabilities(tuple(value/normalizer for value in rational_weights), support, len(features))
            selected = tuple(_evaluate(value/scale, precision) for value, scale in zip(theta, scales))
            lookup = dict(zip(basis, selected))
            multipliers = sp.Tuple(*(lookup.get(column, sp.S.Zero) for column in range(len(targets))))
            return p, multipliers, iteration
        if iteration == MAX_ITERATIONS:
            break
        try:
            step = covariance.inv()*gradient
        except (ValueError, ZeroDivisionError, sp.matrices.exceptions.NonInvertibleMatrixError) as error:
            raise ValueError("La covarianza numérica está mal condicionada; aumente precisión o reformule observables.") from error
        largest_step = max(abs(value) for value in step)
        if largest_step > 100:
            step *= 100/largest_step
        descent = (gradient.T*step)[0]
        accepted = False
        for reduction in range(50):
            fraction = sp.Rational(1, 2**reduction)
            candidate_theta = theta-fraction*step
            try:
                candidate = state(candidate_theta)
            except ValueError:
                continue
            new_error = max(abs(value) for value in candidate[1])
            if (candidate[3] <= objective-sp.Rational(1, 10000)*fraction*descent or
                    new_error < error and candidate[3] <= objective+rounding*(1+abs(objective))):
                theta, current, accepted = candidate_theta, candidate, True
                break
        if not accepted:
            raise ValueError("La búsqueda amortiguada MaxEnt no convergió; no se informa una solución.")
    raise ValueError("MaxEnt no convergió en 200 iteraciones; esto no prueba infactibilidad.")


def solution_diagnostics(features, targets, reference, probabilities, multipliers, support, precision):
    """Recompute residuals from stored data without linear programming or optimization."""
    first = support[0]
    residuals = sp.Tuple(*(sp.Add(*(probabilities[index]*features[index][column] for index in support))-target
                           for column, target in enumerate(targets)))
    _coefficient_budget((*residuals, *multipliers))
    stationarity = tuple(sp.log(probabilities[index]/reference[index])-sp.log(probabilities[first]/reference[first])
                         +sp.Add(*(coefficient*(features[index][column]-features[first][column])
                                   for column, coefficient in enumerate(multipliers))) for index in support)
    exact = precision == 0
    if exact:
        if any(value != 0 for value in residuals):
            raise ValueError("La solución cerrada no satisface las restricciones exactas.")
        stationarity = tuple(sp.expand(sp.expand_log(value, force=True)) for value in stationarity)
        if any(value != 0 for value in stationarity):
            raise ValueError("No se verificó exactamente la condición de optimalidad del caso cerrado.")
        stationarity_residual = sp.S.Zero
        logz = -sp.log(probabilities[first]/reference[first])-sp.Add(*(
            coefficient*features[first][column] for column, coefficient in enumerate(multipliers)))
        gap = sp.S.Zero
    else:
        working = precision+35
        stationarity_residual = max(abs(_evaluate(value, working)) for value in stationarity)
        logits = tuple(sp.log(reference[index])-sp.Add(*(
            coefficient*(features[index][column]-features[first][column])
            for column, coefficient in enumerate(multipliers))) for index in support)
        evaluated = tuple(_evaluate(value, working) for value in logits)
        shift = max(evaluated)
        logz_relative = shift+sp.log(sp.Add(*(sp.exp(value-shift) for value in evaluated)))
        logz = logz_relative-sp.Add(*(coefficient*features[first][column]
                                     for column, coefficient in enumerate(multipliers)))
        kl = sp.Add(*(probabilities[index]*sp.log(probabilities[index]/reference[index]) for index in support))
        gap = _evaluate(kl+logz_relative+sp.Add(*(coefficient*(targets[column]-features[first][column])
                                                for column, coefficient in enumerate(multipliers))), working)
        tolerance = sp.Float(10, working)**(-max(5, precision-10))
        scaled = []
        for column, residual in enumerate(residuals):
            values = tuple(features[index][column] for index in support)
            span = max(values)-min(values)
            if span:
                edge = min(targets[column]-min(values), max(values)-targets[column])
                scale = min(span, edge) if edge > 0 else span
            else:
                scale = sp.S.One
            scaled.append(abs(_evaluate(residual/scale, working)))
        if max((*scaled, stationarity_residual, abs(gap))) > tolerance:
            raise ValueError("Los residuos almacenados no satisfacen la precisión solicitada de MaxEnt.")
    return {"residuals": residuals, "stationarity_residual": stationarity_residual,
            "dual_gap": gap, "logz": logz if exact else _evaluate(logz, precision)}


def solve_maxent(features, targets, reference=None, precision=50, geometry=None):
    """Minimize KL on a finite feasible face; exact cases precede damped Newton.

    Numerical stopping uses centered/scaled constraint residuals, stationarity
    and an estimated dual gap with absolute/relative scale 10**(-(digits-10)).
    These numerical diagnostics do not constitute certified interval bounds.
    """
    precision = _precision(precision)
    if geometry is None:
        from .maxent_geometry import prepare_problem
        geometry = prepare_problem(features, targets, reference)
    features, targets, reference = geometry["features"], geometry["targets"], geometry["reference"]
    support, basis = tuple(geometry["support"]), tuple(geometry["basis"])
    exact = _exact_solution(features, targets, reference, support, basis, geometry["feasible"])
    if exact is not None:
        probabilities, method = exact
        multipliers = _exact_dual(features, reference, probabilities, support, basis)
        actual_precision, iterations = 0, 0
    else:
        probabilities, multipliers, iterations = _newton(features, targets, reference, support, basis, precision,
                                                        geometry["feasible"])
        method, actual_precision = "damped_newton", precision
    diagnostics = solution_diagnostics(features, targets, reference, probabilities, multipliers, support, actual_precision)
    if actual_precision == 0 and any(value != 0 for value in diagnostics["residuals"]):
        raise ValueError("La solución cerrada no satisface las restricciones exactas.")
    return {"features": features, "targets": targets, "reference": reference,
            "probabilities": probabilities, "multipliers": multipliers,
            "support": sp.Tuple(*support), "basis": sp.Tuple(*basis), "precision": actual_precision,
            "iterations": iterations, "method": method, "boundary": bool(geometry["boundary"]),
            "rank": int(geometry["rank"]), "face_certificate": geometry.get("face_certificate", sp.Tuple()),
            "feasible": geometry["feasible"],
            **diagnostics}
