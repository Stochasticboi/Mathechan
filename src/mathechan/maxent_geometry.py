"""Exact finite moment geometry with independently checked LP witnesses."""

from itertools import combinations
import math

import sympy as sp
from sympy.solvers.simplex import linprog, InfeasibleLPError, UnboundedLPError

MAX_STATES = 32
MAX_OBSERVABLES = 4
MAX_INPUT_BITS = 4096
MAX_OUTPUT_BITS = 12000
MAX_BASES = 20000


class InfeasibleMomentsError(ValueError):
    """The declared finite moment constraints have been proved infeasible."""


class GeometryBudgetError(ValueError):
    """The geometry could not be established within the exact search budget."""


def _rational(value):
    if type(value) is int:
        value = sp.Integer(value)
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("Los datos MaxEnt deben ser finitos.")
        value = sp.Float(value)
    if isinstance(value, sp.Float):
        if abs(value._mpf_[2]) > 10000 or value._prec > 4096:
            raise ValueError("El dato aproximado excede el presupuesto de precisión o exponente.")
        value = sp.Rational(value)
    if not isinstance(value, sp.Rational):
        raise ValueError("MaxEnt requiere datos racionales numéricos; use N para aproximar otros números reales.")
    if max(abs(int(value.p)).bit_length(), int(value.q).bit_length()) > MAX_INPUT_BITS:
        raise ValueError("Los coeficientes de MaxEnt exceden 4096 bits.")
    return value


def normalize_problem(features, targets, reference=None):
    """Validate rational inputs without running an optimizer or an LP."""
    raw_inputs = (features, targets) if reference is None else (features, targets, reference)
    approximate = any(isinstance(value, sp.Basic) and value.has(sp.Float)
                      for value in raw_inputs)
    if isinstance(features, sp.MatrixBase):
        raw_rows = [list(features.row(index)) for index in range(features.rows)]
    elif isinstance(features, (tuple, list, sp.Tuple)):
        raw_rows = list(features)
        if raw_rows and not isinstance(raw_rows[0], (tuple, list, sp.Tuple)):
            raw_rows = [[value] for value in raw_rows]
    else:
        raise ValueError("Los observables requieren una tabla por estados o un vector escalar.")
    if not 1 <= len(raw_rows) <= MAX_STATES:
        raise ValueError("MaxEnt admite de uno a 32 estados.")
    if any(not isinstance(row, (tuple, list, sp.Tuple)) for row in raw_rows):
        raise ValueError("La tabla de observables debe ser rectangular.")
    columns = len(raw_rows[0])
    if not 1 <= columns <= MAX_OBSERVABLES or any(len(row) != columns for row in raw_rows):
        raise ValueError("MaxEnt admite de uno a cuatro observables por estado.")
    if isinstance(targets, sp.MatrixBase):
        if targets.rows != 1 and targets.cols != 1:
            raise ValueError("Las medias objetivo requieren un vector.")
        raw_targets = list(targets)
    elif isinstance(targets, (tuple, list, sp.Tuple)):
        raw_targets = list(targets)
    else:
        raw_targets = [targets]
    if len(raw_targets) != columns:
        raise ValueError("Se requiere una media objetivo por observable.")
    count = len(raw_rows)
    if reference is None:
        raw_reference = [sp.Rational(1, count)]*count
    elif isinstance(reference, (tuple, list, sp.Tuple)):
        raw_reference = list(reference)
    else:
        raise ValueError("La referencia requiere una lista de probabilidades.")
    if len(raw_reference) != count:
        raise ValueError("La referencia debe tener una probabilidad por estado.")
    flat = [value for row in raw_rows for value in row] + raw_targets + raw_reference
    approximate = approximate or any(isinstance(value, (float, sp.Float)) for value in flat)
    rows = sp.Tuple(*(sp.Tuple(*(_rational(value) for value in row)) for row in raw_rows))
    means = sp.Tuple(*(_rational(value) for value in raw_targets))
    prior = sp.Tuple(*(_rational(value) for value in raw_reference))
    if sum(int(sp.count_ops(value)) for value in (*[entry for row in rows for entry in row], *means, *prior)) > 256:
        raise ValueError("Los datos MaxEnt exceden 256 operaciones de entrada.")
    if any(value < 0 for value in prior) or sum(prior) != 1:
        raise ValueError("La referencia debe ser no negativa y sumar exactamente uno; normalice sus pesos antes de MaxEnt.")
    return {"features": rows, "targets": means, "reference": prior,
            "input_approximate": bool(approximate)}


def _output_budget(values):
    if any(not isinstance(value, sp.Rational) or
           max(abs(int(value.p)).bit_length(), int(value.q).bit_length()) > MAX_OUTPUT_BITS
           for value in values):
        raise GeometryBudgetError("Los testigos geométricos exceden 12000 bits racionales.")


def _candidate_lp(c, A, b):
    try:
        value, solution = linprog(list(c), [[0]*A.cols], [0], A, b)
    except (InfeasibleLPError, UnboundedLPError, ValueError, TypeError, ZeroDivisionError, NotImplementedError):
        return None
    if len(solution) != A.cols:
        return None
    p = sp.Matrix(solution)
    if any(not isinstance(item, sp.Rational) or item < 0 for item in p) or A*p != b:
        return None
    _output_budget(p)
    if sum(coefficient*probability for coefficient, probability in zip(c, p)) != value:
        return None
    return p


def _dual_zero_certificate(index, A, b):
    """Certify p[index]<=0; never trust an unchecked backend optimum."""
    c = sp.Matrix([-int(j == index) for j in range(A.cols)])
    dimension = A.rows
    try:
        _, split = linprog(list(-b)+list(b), A.T.row_join(-A.T), list(c))
    except (InfeasibleLPError, UnboundedLPError, ValueError, TypeError, ZeroDivisionError, NotImplementedError):
        return None
    if len(split) != 2*dimension:
        return None
    y = sp.Matrix(split[:dimension])-sp.Matrix(split[dimension:])
    if any(not isinstance(value, sp.Rational) for value in y):
        return None
    if any(value < 0 for value in c-A.T*y) or (b.T*y)[0] != 0:
        return None
    certificate = -y
    _output_budget(certificate)
    return certificate


def _enumerate_face(A, b):
    """Fallback basic feasible vertices, stopping early only for full support."""
    rows = list(A.T.rref()[1])
    reduced = A[rows, :]
    rhs = b[rows, :]
    rank = len(rows)
    total = math.comb(A.cols, rank)
    witnesses = []
    support = set()
    for checked, basis in enumerate(combinations(range(A.cols), rank), start=1):
        if checked > MAX_BASES:
            raise GeometryBudgetError("La geometría no pudo certificarse dentro de 20000 bases exactas.")
        square = reduced[:, list(basis)]
        if square.det() == 0:
            continue
        values = square.inv()*rhs
        if any(value < 0 for value in values):
            continue
        p = sp.zeros(A.cols, 1)
        for index, value in zip(basis, values):
            p[index] = value
        if A*p != b:
            continue
        _output_budget(p)
        witnesses.append(p)
        support.update(index for index, value in enumerate(p) if value > 0)
        if len(support) == A.cols:
            return witnesses, support
    if not witnesses:
        if total <= MAX_BASES:
            raise InfeasibleMomentsError("Las medias objetivo no pertenecen al conjunto convexo permitido por la referencia.")
        raise GeometryBudgetError("No se encontró un testigo dentro del presupuesto geométrico.")
    return witnesses, support


def _valid_face(certificate, A, b, support):
    values = A.T*certificate
    return ((b.T*certificate)[0] == 0 and
            all(value == 0 if index in support else value >= 1
                for index, value in enumerate(values)))


def _face_certificate(A, b, support, known):
    if len(support) == A.cols:
        return sp.zeros(A.rows, 1)
    certificate = sum(known, sp.zeros(A.rows, 1))
    if _valid_face(certificate, A, b, support):
        return certificate
    active = sorted(support)
    excluded = [index for index in range(A.cols) if index not in support]
    # Reduce to the nullspace of the active face, then solve inequalities in
    # its independent directions. Variables are split to avoid relying on
    # unrestricted-variable handling in the LP backend.
    nullspace = A[:, active].T.nullspace()
    if not nullspace:
        raise GeometryBudgetError("No se obtuvo un expositor del soporte activo.")
    transform = sp.Matrix.hstack(*nullspace)
    inequalities = -A[:, excluded].T*transform
    columns = list(inequalities.rref()[1])
    inequalities = inequalities[:, columns]
    transform = transform[:, columns]
    dimension = len(columns)
    rhs = -sp.ones(len(excluded), 1)
    try:
        _, split = linprog([0]*(2*dimension), inequalities.row_join(-inequalities), rhs)
        if len(split) == 2*dimension:
            z = sp.Matrix(split[:dimension])-sp.Matrix(split[dimension:])
            candidate = transform*z
            if _valid_face(candidate, A, b, support):
                _output_budget(candidate)
                return candidate
    except (InfeasibleLPError, UnboundedLPError, ValueError, TypeError, ZeroDivisionError, NotImplementedError):
        pass
    for checked, selected in enumerate(combinations(range(len(excluded)), dimension), start=1):
        if checked > MAX_BASES:
            break
        square = inequalities[list(selected), :]
        if square.det() == 0:
            continue
        z = square.inv()*rhs[list(selected), :]
        candidate = transform*z
        if _valid_face(candidate, A, b, support):
            _output_budget(candidate)
            return candidate
    raise GeometryBudgetError("No se certificó el soporte activo dentro del presupuesto exacto.")


def prepare_problem(features, targets, reference=None):
    """Return a proved feasible face, its relative-interior witness and rank."""
    result = normalize_problem(features, targets, reference)
    F, m, q = result["features"], result["targets"], result["reference"]
    allowed = [index for index, value in enumerate(q) if value > 0]
    A = sp.Matrix([[1]*len(allowed)]+[[F[index][column] for index in allowed]
                                    for column in range(len(m))])
    b = sp.Matrix([1, *m])
    rank = A.rank()
    if A.row_join(b).rank() != rank:
        raise InfeasibleMomentsError("Las restricciones de medias son linealmente incompatibles.")
    witnesses, certificates = [], []
    if rank == A.cols:
        unique, parameters = A.gauss_jordan_solve(b)
        if parameters.rows or any(value < 0 for value in unique):
            raise InfeasibleMomentsError("La única solución de las medias no es una distribución no negativa.")
        witnesses = [unique]
        support = {index for index, value in enumerate(unique) if value > 0}
    else:
        initial = _candidate_lp([0]*A.cols, A, b)
        if initial is not None:
            witnesses.append(initial)
        support = {index for p in witnesses for index, value in enumerate(p) if value > 0}
        unresolved = set()
        for index in range(A.cols):
            if index in support:
                continue
            candidate = _candidate_lp([-int(j == index) for j in range(A.cols)], A, b)
            if candidate is not None and candidate[index] > 0:
                witnesses.append(candidate)
                support.update(j for j, value in enumerate(candidate) if value > 0)
                continue
            certificate = _dual_zero_certificate(index, A, b)
            if certificate is not None:
                certificates.append(certificate)
            else:
                unresolved.add(index)
        if not witnesses or unresolved-support:
            witnesses, support = _enumerate_face(A, b)
    certificate = _face_certificate(A, b, support, certificates)
    relative = sum(witnesses, sp.zeros(A.cols, 1))/len(witnesses)
    if A*relative != b or any(value <= 0 if index in support else value != 0
                              for index, value in enumerate(relative)):
        raise GeometryBudgetError("No se obtuvo un testigo interior relativo válido.")
    _output_budget(relative)
    full = [sp.S.Zero]*len(F)
    for index, value in zip(allowed, relative):
        full[index] = value
    active = sorted(allowed[index] for index in support)
    augmented_features = sp.Matrix([[1, *F[index]] for index in active])
    pivots = augmented_features.rref()[1]
    basis = tuple(column-1 for column in pivots if column != 0)
    result.update(support=tuple(active), basis=basis, rank=len(basis),
                  boundary=len(active) < len(allowed), feasible=sp.Tuple(*full),
                  face_certificate=sp.Tuple(*certificate))
    return result
