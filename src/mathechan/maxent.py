"""Validated finite maximum-entropy results, including durable face witnesses."""

import sympy as sp
from sympy.core.symbol import Str

from .calculus import OperationOutcome
from .finite_probability import FiniteDistribution
from .maxent_geometry import normalize_problem
from .maxent_solver import METHODS, solution_diagnostics, solve_maxent

MAXENT_CALLS = frozenset({
    "MaxEnt", "RelEntropy", "Means", "Residuals", "Dual", "FaceDual", "DualGap",
    "Active", "Rank", "Converged", "Score", "Targets",
})
QUERIES = MAXENT_CALLS | {"Probabilities", "Dist", "Entropy", "LogZ"}


def _integer(value, low, high):
    if type(value) is int:
        value = sp.Integer(value)
    if not isinstance(value, sp.Integer) or not low <= value <= high:
        raise ValueError("Metadato entero MaxEnt fuera de rango.")
    return value


def _vector(raw, length):
    if not isinstance(raw, (tuple, list, sp.Tuple)) or len(raw) != length:
        raise ValueError("Dimensiones incompatibles en el resultado MaxEnt.")
    values = sp.Tuple(*raw)
    for value in values:
        if (not isinstance(value, sp.Rational) or
                max(abs(int(value.p)).bit_length(), int(value.q).bit_length()) > 12000):
            raise ValueError("Los pesos y testigos MaxEnt requieren racionales de hasta 12000 bits.")
    return values


def _indices(raw, maximum):
    if not isinstance(raw, (tuple, list, sp.Tuple)):
        raise ValueError("Los índices MaxEnt requieren una lista.")
    values = sp.Tuple(*(_integer(value, 0, maximum-1) for value in raw))
    if tuple(values) != tuple(sorted(set(values))):
        raise ValueError("Los índices MaxEnt deben estar ordenados y no repetirse.")
    return values


class MaxEntResult(sp.Basic):
    """A checked solution; loading checks witnesses but never repeats inference."""

    def __new__(cls, features, targets, reference, probabilities, multipliers,
                support, basis, face_certificate, feasible, precision, iterations,
                method, objective, input_approximate=sp.false):
        problem = normalize_problem(features, targets, reference)
        features, targets, reference = (problem[key] for key in ("features", "targets", "reference"))
        n, k = len(features), len(targets)
        probabilities, feasible = _vector(probabilities, n), _vector(feasible, n)
        support, basis = _indices(support, n), _indices(basis, k)
        certificate = _vector(face_certificate, k+1)
        if not support or any(reference[index] <= 0 for index in support):
            raise ValueError("El soporte activo debe estar permitido por la referencia.")
        for vector in (probabilities, feasible):
            if sum(vector) != 1 or any(value < 0 for value in vector):
                raise ValueError("Los pesos MaxEnt deben ser no negativos y sumar exactamente uno.")
            if any((vector[index] > 0) != (index in support) for index in range(n)):
                raise ValueError("Los pesos y el testigo deben tener exactamente el soporte declarado.")
        if any(sum(feasible[index]*features[index][column] for index in support) != target
               for column, target in enumerate(targets)):
            raise ValueError("El testigo exacto no satisface las medias declaradas.")
        if certificate[0]+sum(certificate[column+1]*target for column, target in enumerate(targets)) != 0:
            raise ValueError("El certificado de la cara no contiene las medias objetivo.")
        for index, row in enumerate(features):
            if reference[index] == 0:
                continue
            score = certificate[0]+sum(value*coefficient for value, coefficient in zip(row, certificate[1:]))
            if (index in support and score != 0) or (index not in support and score < 1):
                raise ValueError("El certificado no demuestra el soporte factible declarado.")
        affine = sp.Matrix([[1, *features[index]] for index in support])
        expected_basis = tuple(index-1 for index in affine.rref()[1] if index)
        if tuple(basis) != expected_basis:
            raise ValueError("La base declarada no corresponde al rango afín de los observables.")
        precision, iterations = _integer(precision, 0, 100), _integer(iterations, 0, 200)
        method, objective = str(method), str(objective)
        if method not in METHODS or objective not in {"shannon", "relative"}:
            raise ValueError("Método u objetivo MaxEnt desconocido.")
        if (method == "damped_newton") != (precision >= 10) or precision and precision < 10:
            raise ValueError("El método y la precisión MaxEnt son incompatibles.")
        if precision == 0 and iterations != 0:
            raise ValueError("Un caso cerrado no registra iteraciones numéricas.")
        if method == "exact_face_prior" and probabilities != sp.Tuple(*(
                reference[index]/sum(reference[j] for j in support) if index in support else 0
                for index in range(n))):
            raise ValueError("Los pesos no corresponden a la referencia condicionada declarada.")
        if method == "exact_unique" and len(basis) != len(support)-1:
            raise ValueError("Las restricciones no determinan una solución factible única.")
        if method == "exact_two_groups" and (len(basis) != 1 or
                len({features[index][basis[0]] for index in support}) != 2):
            raise ValueError("El método cerrado requiere dos grupos de valores.")
        if objective == "shannon" and any(value != sp.Rational(1, n) for value in reference):
            raise ValueError("Shannon sin referencia explícita requiere la referencia uniforme.")
        if input_approximate not in (sp.true, sp.false) or type(input_approximate) is bool:
            raise ValueError("El indicador de datos aproximados requiere un booleano matemático.")
        if not isinstance(multipliers, (tuple, list, sp.Tuple)) or len(multipliers) != k:
            raise ValueError("Se requiere un multiplicador por observable.")
        multipliers = sp.Tuple(*multipliers)
        for coefficient in multipliers:
            if (not isinstance(coefficient, sp.Expr) or coefficient.free_symbols or
                    coefficient.is_real is not True or coefficient.has(sp.oo, -sp.oo, sp.zoo, sp.nan)
                    or sp.count_ops(coefficient) > 256):
                raise ValueError("Los multiplicadores requieren constantes reales finitas.")
            if any(abs(value._mpf_[2]) > 10000 or value._prec > 4096 for value in coefficient.atoms(sp.Float)):
                raise ValueError("Un multiplicador aproximado excede el presupuesto.")
        if any(value != 0 for column, value in enumerate(multipliers) if column not in basis):
            raise ValueError("Los multiplicadores redundantes deben usar la convención cero.")
        diagnostics = solution_diagnostics(features, targets, reference, probabilities,
                                           multipliers, tuple(support), int(precision))
        if precision == 0 and any(value != 0 for value in diagnostics['residuals']):
            raise ValueError("La solución exacta no satisface todas las medias.")
        return sp.Basic.__new__(cls, features, targets, reference, probabilities, multipliers,
                                support, basis, certificate, feasible, precision, iterations,
                                Str(method), Str(objective), input_approximate)

    features = property(lambda self: self.args[0])
    targets = property(lambda self: self.args[1])
    reference = property(lambda self: self.args[2])
    probabilities = property(lambda self: self.args[3])
    multipliers = property(lambda self: self.args[4])
    support = property(lambda self: self.args[5])
    basis = property(lambda self: self.args[6])
    face_certificate = property(lambda self: self.args[7])
    feasible = property(lambda self: self.args[8])
    precision = property(lambda self: int(self.args[9]))
    iterations = property(lambda self: int(self.args[10]))
    method = property(lambda self: str(self.args[11]))
    objective = property(lambda self: str(self.args[12]))
    input_approximate = property(lambda self: self.args[13] is sp.true)
    boundary = property(lambda self: len(self.support) < sum(bool(value > 0) for value in self.reference))

    def diagnostics(self):
        values = solution_diagnostics(self.features, self.targets, self.reference,
                                       self.probabilities, self.multipliers, tuple(self.support), self.precision)
        return {"method": self.method, "objective": self.objective, "precision": self.precision,
                "iterations": self.iterations, "converged": True, "rank": len(self.basis),
                "observables": len(self.targets), "states": len(self.features),
                "active_states": [int(index)+1 for index in self.support],
                "boundary": self.boundary, "dual_scope": "active_face" if self.boundary else "reference_support",
                "feasibility": "exact_rational_witness", "face_validation": "exact_exposing_certificate",
                "normalization_residual": "0", "constraint_residuals": list(map(sp.sstr, values['residuals'])),
                "stationarity_residual": sp.sstr(values['stationarity_residual']),
                "estimated_dual_gap": sp.sstr(values['dual_gap']),
                "input_approximate": self.input_approximate, "precision_certified": False,
                "partition_convention": "normalized_reference", "dual_gauge": "redundant_columns_zero"}

    def _sympystr(self, printer):
        return f'MaxEntResult[states={len(self.features)},rank={len(self.basis)},method={self.method},boundary={self.boundary}]'


def maxent_operation(name, args, assumptions=sp.true):
    if name == "MaxEnt":
        if not 2 <= len(args) <= 4:
            raise ValueError("Use MaxEnt[F,medias], con referencia y precisión opcionales.")
        reference = args[2] if len(args) >= 3 else None
        precision = args[3] if len(args) == 4 else sp.Integer(50)
        from .maxent_geometry import prepare_problem
        geometry = prepare_problem(args[0], args[1], reference)
        solution = solve_maxent(args[0], args[1], reference, precision, geometry)
        value = MaxEntResult(geometry['features'], geometry['targets'], geometry['reference'],
                            solution['probabilities'], solution['multipliers'], solution['support'],
                            solution['basis'], geometry['face_certificate'], geometry['feasible'],
                            solution['precision'], solution['iterations'], solution['method'],
                            "shannon" if reference is None else "relative",
                            sp.true if geometry['input_approximate'] else sp.false)
        return OperationOutcome(value, details=value.diagnostics()), ()
    if len(args) != 1 or not isinstance(args[0], MaxEntResult) or name not in QUERIES:
        raise ValueError("La consulta requiere un resultado creado con MaxEnt.")
    result = args[0]
    details = result.diagnostics()
    diagnostic = solution_diagnostics(result.features, result.targets, result.reference,
                                      result.probabilities, result.multipliers, tuple(result.support), result.precision)
    if name == "Probabilities":
        value = (sp.Tuple(*(p.evalf(result.precision) for p in result.probabilities))
                 if result.precision else result.probabilities)
    elif name == "Dist":
        value = FiniteDistribution(sp.Tuple(*range(1, len(result.features)+1)), result.probabilities)
    elif name in {"Entropy", "RelEntropy", "Score"}:
        entropy = -sp.Add(*(p*sp.log(p) for p in result.probabilities if p))
        relative = sp.Add(*(p*sp.log(p/q) for p, q in zip(result.probabilities, result.reference) if p))
        value = entropy if name == "Entropy" else relative if name == "RelEntropy" else (
            entropy if result.objective == "shannon" else -relative)
        value = value.evalf(result.precision) if result.precision else sp.simplify(value)
    elif name in {"Dual", "FaceDual"}:
        if name == "Dual" and result.boundary:
            raise ValueError("Esta solución está en la frontera; no tiene multiplicadores globales finitos. Use FaceDual para la cara activa.")
        value = result.multipliers
    elif name == "Targets":
        value = result.targets
    elif name == "Means":
        value = sp.Tuple(*(target+residual for target, residual in zip(result.targets, diagnostic['residuals'])))
        if result.precision:
            value = sp.Tuple(*(item.evalf(result.precision) for item in value))
    elif name == "Residuals":
        value = diagnostic['residuals']
    elif name == "DualGap":
        value = diagnostic['dual_gap']
    elif name == "LogZ":
        value = diagnostic['logz']
    elif name == "Rank":
        value = sp.Integer(len(result.basis))
    elif name == "Active":
        value = sp.Tuple(*(index+1 for index in result.support))
    else:
        value = sp.true
    if sp.count_ops(value) > 4096:
        raise ValueError("La consulta MaxEnt excede 4096 operaciones.")
    warnings = []
    if result.precision or result.input_approximate:
        warnings.append("La normalización es exacta para los pesos almacenados; los residuos numéricos no certifican incertidumbre experimental ni cotas rigurosas de optimalidad.")
    if result.boundary and name == "FaceDual":
        warnings.append("Los multiplicadores pertenecen sólo a la cara activa; no son multiplicadores globales finitos.")
    return OperationOutcome(value, warnings=tuple(warnings), details=details), ()
