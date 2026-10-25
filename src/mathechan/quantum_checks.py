"""Bounded operator predicates and a left-to-right partial trace."""

from itertools import combinations, product

import sympy as sp

from .assumptions import predicates
from .calculus import OperationOutcome
from .linear_algebra import _array, _input_budget


def _matrix(value):
    matrix, vector = _array(value)
    if vector or matrix.rows != matrix.cols:
        raise ValueError("Se requiere una matriz cuadrada explícita.")
    _input_budget((matrix,))
    if len(matrix.free_symbols) > 8 or any(item.is_finite is False for item in matrix):
        raise ValueError("La matriz requiere entradas finitas y hasta ocho símbolos.")
    return matrix


def _refine(expression, assumptions):
    try:
        expression = sp.refine(expression, predicates(assumptions))
    except (ValueError, TypeError, NotImplementedError):
        pass
    return sp.simplify(expression)


def _decide(condition, assumptions):
    condition = _refine(condition, assumptions)
    if condition is sp.true or condition is sp.false:
        return condition
    try:
        answer = sp.ask(predicates(condition), predicates(assumptions))
    except (ValueError, TypeError, NotImplementedError):
        answer = None
    return sp.true if answer is True else sp.false if answer is False else condition


def _zero_conditions(matrix, assumptions):
    # Real/imaginary components refine under explicit domains even when
    # SymPy leaves conjugate(symbol) unchanged under Q.real(symbol).
    conditions = []
    for item in matrix:
        conditions.extend((sp.Eq(_refine(sp.re(item), assumptions), 0),
                           sp.Eq(_refine(sp.im(item), assumptions), 0)))
    return sp.And(*conditions)


def _exact_binary(matrix):
    floats = matrix.atoms(sp.Float)
    if any(abs(item._mpf_[2]) > 10000 or item._prec > 4096 for item in floats):
        raise ValueError("Los decimales exceden el presupuesto de exponente o precisión.")
    return matrix.xreplace({item: sp.Rational(item) for item in floats}), bool(floats)


def _result(value, operation, warnings=(), **details):
    # Keep zero tests as logical membership predicates, distinct from inert
    # user equations, including when embedded in mixed lists or saved sessions.
    if operation != "PTrace":
        value = value.replace(
            lambda item: isinstance(item, sp.Equality),
            lambda item: sp.Contains(item.lhs-item.rhs, sp.FiniteSet(0)),
        )
    if sp.count_ops(value) > 4096:
        raise ValueError("El resultado excede 4096 operaciones.")
    if value.has(sp.nan, sp.zoo, sp.oo, -sp.oo):
        raise ValueError("El resultado contiene valores no finitos.")
    return OperationOutcome(value, warnings=tuple(warnings), details={
        "operation": operation, "method": "exact_matrix_identities",
        "sympy_version": sp.__version__, "precision_certified": False,
        **details,
    }), ()


def _partial_trace(matrix, dimensions, traced):
    if (not isinstance(dimensions, (tuple, list, sp.Tuple)) or not 1 <= len(dimensions) <= 4
            or any(isinstance(item, bool) or not isinstance(item, (int, sp.Integer))
                   or not 1 <= int(item) <= 8 for item in dimensions)):
        raise ValueError("Las dimensiones deben ser una lista de uno a cuatro enteros positivos hasta ocho.")
    dimensions = tuple(map(int, dimensions))
    if sp.prod(dimensions) != matrix.rows:
        raise ValueError("El producto de dimensiones debe coincidir con el orden de la matriz.")
    traced = tuple(traced) if isinstance(traced, (tuple, list, sp.Tuple)) else (traced,)
    if (any(isinstance(item, bool) or not isinstance(item, (int, sp.Integer))
            or not 1 <= int(item) <= len(dimensions) for item in traced)
            or len(set(traced)) != len(traced)):
        raise ValueError("Los subsistemas a trazar deben ser índices distintos desde uno.")
    traced = tuple(sorted(int(item)-1 for item in traced))
    kept = tuple(index for index in range(len(dimensions)) if index not in traced)
    details = {
        "method": "finite_partial_trace", "dimensions": list(dimensions),
        "traced_subsystems": [index+1 for index in traced],
        "remaining_dimensions": [dimensions[index] for index in kept],
        "subsystem_order": "left_to_right_most_significant_first",
    }
    if not traced:
        return matrix.as_immutable(), details
    if not kept:
        return sp.trace(matrix), details
    kept_states = tuple(product(*(range(dimensions[index]) for index in kept)))
    traced_states = tuple(product(*(range(dimensions[index]) for index in traced)))

    def position(kept_coordinates, traced_coordinates):
        coordinates = dict(zip(kept, kept_coordinates))
        coordinates.update(zip(traced, traced_coordinates))
        offset = 0
        for index, dimension in enumerate(dimensions):
            offset = offset*dimension+coordinates[index]
        return offset

    result = sp.ImmutableMatrix(len(kept_states), len(kept_states), lambda row, column:
        sp.Add(*(matrix[position(kept_states[row], sample), position(kept_states[column], sample)]
                 for sample in traced_states)))
    return result, details


def check_operation(name, args, assumptions=sp.true):
    """Return a boolean formula or partial trace, never guess undecided tests.

    PSDCheck means Hermitian positive semidefinite, including the zero matrix.
    Floating predicates classify exact stored binary entries without tolerance.
    """
    if name not in {"HermQ", "UnitaryQ", "PSDCheck", "PTrace"}:
        raise ValueError("Comprobación de operador desconocida.")
    if len(args) != (3 if name == "PTrace" else 1):
        raise ValueError("Número de argumentos incorrecto para la operación.")
    matrix = _matrix(args[0])
    if name == "PSDCheck" and matrix.rows > 4:
        raise ValueError("PSDCheck admite matrices de hasta cuatro por cuatro.")
    if name == "PTrace":
        value, details = _partial_trace(matrix, args[1], args[2])
        warnings = ("La suma de entradas aproximadas no certifica precisión ni incertidumbre de los datos.",) if matrix.has(sp.Float) else ()
        return _result(value, name, warnings, **details)
    matrix, floating = _exact_binary(matrix)
    warnings = ()
    if floating:
        warnings = ("La comprobación usa exactamente los valores binarios almacenados, sin tolerancia; no certifica incertidumbre física ni dígitos correctos.",)
    if name == "UnitaryQ":
        value = _zero_conditions(matrix.H*matrix-sp.eye(matrix.rows), assumptions)
        return _result(_decide(value, assumptions), name, warnings,
                       float_policy="exact_stored_binary_no_tolerance", identity="A.H*A=Identity")
    hermitian = _decide(_zero_conditions(matrix-matrix.H, assumptions), assumptions)
    if name == "HermQ":
        return _result(hermitian, name, warnings, float_policy="exact_stored_binary_no_tolerance")
    if hermitian is sp.false:
        return _result(sp.false, name, warnings, definition="Hermitian_positive_semidefinite")
    conditions = [hermitian]
    for size in range(1, matrix.rows+1):
        for indices in combinations(range(matrix.rows), size):
            minor = sp.simplify(matrix.extract(indices, indices).det())
            real = _refine(sp.re(minor), assumptions)
            imaginary = _refine(sp.im(minor), assumptions)
            conditions.extend((sp.Eq(imaginary, 0), sp.Ge(real, 0)))
    value = _decide(sp.And(*conditions), assumptions)
    return _result(value, name, warnings, definition="Hermitian_positive_semidefinite",
                   principal_minors=2**matrix.rows-1, float_policy="exact_stored_binary_no_tolerance")
