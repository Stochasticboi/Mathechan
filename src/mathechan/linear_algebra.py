"""Bounded linear algebra with explicit executable nonsingularity conditions."""

from dataclasses import replace
from itertools import combinations

import sympy as sp

from .calculus import OperationOutcome

MAX_ENTRIES = 64
MAX_DIMENSION = 8
MAX_INPUT_OPERATIONS = 256
MAX_OUTPUT_OPERATIONS = 4096


def _native_number(value):
    if isinstance(value, bool):
        raise ValueError("Un booleano no es una entrada escalar.")
    if isinstance(value, int):
        return sp.Integer(value)
    if isinstance(value, float):
        return sp.Float(value)
    return value


def _scalar(value):
    value = _native_number(value)
    if (not isinstance(value, sp.Expr) or value.is_commutative is not True
            or value.has(sp.nan, sp.zoo, sp.oo, -sp.oo)):
        raise ValueError("Se requieren entradas escalares finitas.")
    return value


def _array(value):
    if isinstance(value, sp.MatrixBase):
        matrix, vector = sp.ImmutableMatrix(value), False
    elif isinstance(value, (list, tuple, sp.Tuple)) and value:
        nested = [isinstance(item, (list, tuple, sp.Tuple)) for item in value]
        if any(nested) and not all(nested):
            raise ValueError("La lista mezcla escalares y filas.")
        if all(nested):
            if not value[0] or any(len(row) != len(value[0]) for row in value):
                raise ValueError("Las filas deben tener la misma longitud positiva.")
            entries = [[_scalar(item) for item in row] for row in value]
            matrix, vector = sp.ImmutableMatrix(entries), False
        else:
            matrix, vector = sp.ImmutableMatrix([_scalar(item) for item in value]), True
    else:
        raise ValueError("Se requiere una matriz rectangular o una lista vectorial no vacía.")
    if (not matrix.rows or not matrix.cols or matrix.rows > MAX_DIMENSION
            or matrix.cols > MAX_DIMENSION or len(matrix) > MAX_ENTRIES):
        raise ValueError("Se admiten hasta ocho filas, ocho columnas y 64 entradas.")
    for item in matrix:
        _scalar(item)
    return matrix, vector


def _input_budget(values):
    entries = []
    for value in values:
        if isinstance(value, (sp.MatrixBase, list, tuple, sp.Tuple)):
            matrix, _ = _array(value)
            entries.extend(matrix)
        else:
            entries.append(_scalar(value))
    if sum(int(sp.count_ops(item)) for item in entries) > MAX_INPUT_OPERATIONS:
        raise ValueError("La entrada excede 256 operaciones simbólicas.")


def _nonzero(expression, assumptions):
    expression = sp.factor(expression)
    condition = sp.Ne(expression, 0)
    truth = sp.ask(sp.Q.is_true(condition), assumptions)
    if condition is sp.false or truth is False or sp.ask(sp.Q.zero(expression), assumptions) is True:
        raise ValueError("La matriz es singular bajo los supuestos indicados.")
    if condition is sp.true or truth is True or sp.ask(sp.Q.zero(expression), assumptions) is False:
        return ()
    return (condition,)


def _result(value, operation, requirements=(), warnings=(), **details):
    entries = list(value) if isinstance(value, (sp.MatrixBase, sp.Tuple)) else [value]
    if (len(entries) > MAX_ENTRIES
            or sum(int(sp.count_ops(item)) for item in entries) > MAX_OUTPUT_OPERATIONS):
        raise ValueError("El resultado excede 64 entradas o 4096 operaciones.")
    if any(item.has(sp.nan, sp.zoo, sp.oo, -sp.oo) for item in entries):
        raise ValueError("El resultado contiene valores no finitos.")
    outcome = OperationOutcome(
        value, "conditional" if requirements else "evaluated",
        tuple(sp.sstr(item) for item in requirements), tuple(warnings),
        {"method": "sympy.matrices", "operation": operation,
         "sympy_version": sp.__version__, "input_limit_entries": MAX_ENTRIES,
         "domain_analysis": "partial", **details},
    )
    return outcome, tuple(requirements)


def _conditioning(matrix, warnings, details):
    if not matrix.atoms(sp.Float):
        return
    if not any("Entradas aproximadas" in warning for warning in warnings):
        warnings.append("Entradas aproximadas: los ceros y rangos no usan una tolerancia numérica configurable.")
    if matrix.rows != matrix.cols or matrix.free_symbols:
        return
    try:
        estimate = (matrix.norm(sp.oo) * matrix.inv().norm(sp.oo)).evalf()
        details["condition_estimate_infinity_norm"] = sp.sstr(estimate)
        if estimate.is_finite is False or estimate > 10**12:
            warnings.append("La matriz está mal condicionada; el resultado puede perder precisión.")
    except (ValueError, TypeError, ZeroDivisionError, NotImplementedError):
        details["condition_estimate_infinity_norm"] = "unavailable"


def _rank(matrix, assumptions):
    """Certify a rank branch by one nonzero maximal minor, never universalize it."""
    substitutions = {}
    for equality in assumptions.atoms(sp.Equality):
        if isinstance(equality.lhs, sp.Symbol) and not equality.rhs.free_symbols:
            substitutions[equality.lhs] = equality.rhs
        elif isinstance(equality.rhs, sp.Symbol) and not equality.lhs.free_symbols:
            substitutions[equality.rhs] = equality.lhs
    if substitutions:
        matrix = matrix.subs(substitutions, simultaneous=True)
    rank = matrix.rank()
    if rank == 0:
        return sp.Integer(0), ()
    candidate = None
    examined = 0
    for rows in combinations(range(matrix.rows), rank):
        for cols in combinations(range(matrix.cols), rank):
            minor = sp.factor(matrix.extract(rows, cols).det())
            examined += 1
            if minor == 0:
                continue
            try:
                requirements = _nonzero(minor, assumptions)
            except ValueError:
                continue
            if not requirements:
                return sp.Integer(rank), ()
            if candidate is None:
                candidate = requirements
            if examined >= 256:
                break
        if examined >= 256:
            break
    if candidate is not None:
        return sp.Integer(rank), candidate
    raise ValueError("El rango depende de los parámetros; especifique supuestos adicionales.")


def matrix_operation(name, args, assumptions=sp.true):
    """Return (OperationOutcome, executable requirements) for a bounded operation.

    Flat lists are unoriented vectors for Dot: contraction is bilinear, without
    complex conjugation. Matrix objects keep their explicit row/column shape.
    """
    arities = {"Dimensions": 1, "Dot": 2, "Transpose": 1, "Tr": 1, "Det": 1,
               "Inverse": 1, "MatrixRank": 1, "LinearSolve": 2, "MatrixPower": 2}
    if name not in arities or len(args) != arities[name]:
        raise ValueError("Operación matricial desconocida o número de argumentos incorrecto.")
    _input_budget(args)
    matrix, vector = _array(args[0])
    requirements, warnings, details = (), [], {"input_shape": list(matrix.shape)}
    if matrix.atoms(sp.Float):
        warnings.append("Entradas aproximadas: los ceros y rangos no usan una tolerancia numérica configurable.")
    if name == "Dimensions":
        value = sp.Tuple(matrix.rows) if vector else sp.Tuple(*matrix.shape)
    elif name == "Dot":
        other, other_vector = _array(args[1])
        if vector and other_vector:
            if matrix.rows != other.rows:
                raise ValueError("Los vectores deben tener la misma longitud.")
            value = (matrix.T * other)[0]
        elif vector:
            if matrix.rows != other.rows:
                raise ValueError("Dimensiones incompatibles para el producto vector-matriz.")
            value = sp.Tuple(*(matrix.T * other))
        elif other_vector:
            if matrix.cols != other.rows:
                raise ValueError("Dimensiones incompatibles para el producto matriz-vector.")
            value = sp.Tuple(*(matrix * other))
        else:
            if matrix.cols != other.rows:
                raise ValueError("Dimensiones incompatibles para el producto matricial.")
            value = matrix * other
        details["conjugation"] = "none"
    elif name == "Transpose":
        if vector:
            raise ValueError("Transpose requiere una matriz; una lista plana no tiene orientación.")
        value = matrix.T
    elif name == "MatrixRank":
        value, requirements = _rank(matrix, assumptions)
        if requirements:
            warnings.append("Rango válido en la rama indicada; otras especializaciones requieren recalcularlo.")
    elif name == "LinearSolve":
        rhs, rhs_vector = _array(args[1])
        if rhs.rows != matrix.rows:
            raise ValueError("El término independiente debe tener tantas filas como el sistema.")
        if matrix.rows == matrix.cols and matrix.det() != 0:
            requirements = _nonzero(matrix.det(), assumptions)
            value = matrix.inv() * rhs
            details["solution_type"] = "unique"
        else:
            if matrix.free_symbols:
                raise ValueError("LinearSolve rectangular con coeficientes paramétricos requiere especializar los parámetros.")
            rank = matrix.rank()
            if matrix.row_join(rhs).rank() != rank:
                outcome, conditions = _result(sp.EmptySet, name, solution_type="none")
                return replace(outcome, status="no_solution"), conditions
            value, parameters = matrix.gauss_jordan_solve(rhs)
            if parameters.rows:
                free = [sp.Dummy(f"parameter{index}") for index in range(1, len(parameters) + 1)]
                value = value.xreplace(dict(zip(parameters, free)))
                details["free_parameters"] = [sp.sstr(item) for item in free]
                details["solution_type"] = "family"
                warnings.append("Familia de soluciones: los parámetros libres son escalares complejos arbitrarios.")
            else:
                details["solution_type"] = "unique"
        if (matrix.atoms(sp.Float) or rhs.atoms(sp.Float)) and not value.free_symbols:
            residual = matrix * value - rhs
            residual_norm = max((abs(item.evalf()) for item in residual), default=sp.S.Zero)
            details["residual_max_abs"] = sp.sstr(residual_norm)
            denominator = matrix.norm(sp.oo)*value.norm(sp.oo) + rhs.norm(sp.oo)
            details["relative_backward_error"] = sp.sstr(
                (residual.norm(sp.oo)/denominator).evalf() if denominator != 0 else sp.S.Zero)
        value = sp.Tuple(*value) if rhs_vector else sp.ImmutableMatrix(value)
        _conditioning(matrix, warnings, details)
    else:
        if matrix.rows != matrix.cols or vector:
            raise ValueError("La operación requiere una matriz cuadrada.")
        if name == "Tr":
            value = sp.trace(matrix)
        elif name == "Det":
            value = matrix.det()
        elif name == "Inverse":
            requirements = _nonzero(matrix.det(), assumptions)
            value = matrix.inv()
            _conditioning(matrix, warnings, details)
        else:
            power = _native_number(args[1])
            if not isinstance(power, sp.Integer) or abs(power) > 32:
                raise ValueError("MatrixPower requiere un exponente entero entre -32 y 32.")
            if power < 0:
                requirements = _nonzero(matrix.det(), assumptions)
            value = matrix ** int(power)
    return _result(value, name, requirements, warnings, **details)


def bounded_binary(operator, left, right, assumptions=sp.true):
    """Preserve historical Matrix * Matrix product while bounding basic arithmetic."""
    _input_budget([left, right])
    if operator == "^":
        return matrix_operation("MatrixPower", [left, right], assumptions)
    left_matrix = isinstance(left, (sp.MatrixBase, list, tuple, sp.Tuple))
    right_matrix = isinstance(right, (sp.MatrixBase, list, tuple, sp.Tuple))
    left_vector = right_vector = False
    if left_matrix:
        left, left_vector = _array(left)
    if right_matrix:
        right, right_vector = _array(right)
    else:
        right = _scalar(right)
    if not left_matrix:
        left = _scalar(left)
    if operator in ("+", "-"):
        if (not left_matrix or not right_matrix or left.shape != right.shape
                or left_vector != right_vector):
            raise ValueError("La suma y resta requieren matrices de iguales dimensiones.")
        value = left + right if operator == "+" else left - right
        vector_result = left_vector
    elif operator == "*":
        if left_vector and right_vector:
            raise ValueError("El producto entre vectores requiere Dot para evitar ambigüedad.")
        if left_matrix and right_matrix and (left_vector or right_vector):
            first = sp.Tuple(*left) if left_vector else left
            second = sp.Tuple(*right) if right_vector else right
            return matrix_operation("Dot", [first, second], assumptions)
        if left_matrix and right_matrix and left.cols != right.rows:
            raise ValueError("Dimensiones incompatibles para el producto matricial.")
        value = left * right
        vector_result = left_vector or right_vector
    elif operator == "/":
        if not left_matrix or right_matrix:
            raise ValueError("La división matricial sólo admite matriz dividida por escalar.")
        requirements = _nonzero(_scalar(right), assumptions)
        value = left / right
        return _result(sp.Tuple(*value) if left_vector else sp.ImmutableMatrix(value), operator, requirements)
    else:
        raise ValueError("Operador matricial básico no admitido.")
    return _result(sp.Tuple(*value) if vector_result else sp.ImmutableMatrix(value), operator)
