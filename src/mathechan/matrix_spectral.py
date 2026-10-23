"""Small-matrix spectral operations with explicit generic-branch conditions."""

from itertools import combinations

import sympy as sp

from .calculus import OperationOutcome
from .linear_algebra import _array


def _matrix(argument):
    matrix, vector = _array(argument)
    if vector:
        raise ValueError("La operación espectral requiere una matriz, no una lista vectorial.")
    if not matrix.rows or matrix.rows != matrix.cols:
        raise ValueError("La operación espectral requiere una matriz cuadrada no vacía.")
    if matrix.rows > 4:
        raise ValueError("El presupuesto espectral admite matrices de hasta 4 por 4.")
    if any(not isinstance(item, sp.Expr) or item.is_commutative is not True
           or item.has(sp.nan, sp.zoo, sp.oo, -sp.oo) for item in matrix):
        raise ValueError("Las entradas de la matriz deben ser escalares finitos.")
    operations = sum(int(sp.count_ops(item)) for item in matrix)
    symbols = matrix.free_symbols
    if operations > 256 or len(symbols) > 8:
        raise ValueError("El presupuesto espectral admite 256 operaciones y ocho símbolos.")
    triangular = matrix.is_upper or matrix.is_lower
    if matrix.rows == 4 and (symbols or matrix.has(sp.Float)) and not triangular:
        raise ValueError("Las matrices de orden cuatro con parámetros o decimales deben ser triangulares.")
    if matrix.rows >= 3 and symbols and not triangular and (len(symbols) > 3 or operations > 64):
        raise ValueError("La matriz simbólica densa excede el presupuesto espectral; use una estructura más simple.")
    return matrix


def _requirements(expressions, assumptions):
    requirements = []
    for expression in expressions:
        denominator = sp.denom(sp.together(expression))
        condition = sp.refine(sp.Ne(denominator, 0), assumptions)
        if condition is sp.false:
            raise ValueError("Las hipótesis contradicen el dominio de la operación espectral.")
        if condition is not sp.true and condition not in requirements:
            requirements.append(condition)
    return requirements


def _rank_requirement(matrix, rank, assumptions):
    """A nonzero rank-sized minor certifies the generic eigenspace dimension."""
    if not rank:
        return ()
    candidate = None
    for rows in combinations(range(matrix.rows), rank):
        for columns in combinations(range(matrix.cols), rank):
            minor = sp.factor(matrix.extract(rows, columns).det())
            if minor == 0 or minor.is_zero is True:
                continue
            condition = sp.refine(sp.Ne(minor, 0), assumptions)
            if condition is sp.true:
                return ()
            if condition is not sp.false:
                candidate = condition
    if candidate is None:
        raise ValueError("No se pudo certificar el rango del espacio propio bajo las hipótesis dadas.")
    return (candidate,)


def _atoms(value):
    if isinstance(value, sp.MatrixBase):
        return list(value)
    if isinstance(value, sp.Tuple):
        return [item for child in value for item in _atoms(child)]
    return [value]


def _evaluate(value, digits):
    if isinstance(value, sp.Tuple):
        return sp.Tuple(*(_evaluate(child, digits) for child in value))
    return value.evalf(digits)


def spectral_operation(name, args, assumptions=sp.true):
    """Return (outcome, executable requirements), without modifying session state.

    Eigenvectors returns right, non-normalized vectors grouped by eigenvalue.
    Defective matrices return the actual eigenspace bases, never zero padding.
    Floating inputs are exactified as their stored binary rationals before the
    spectral calculation, then evaluated at the least input precision. This
    avoids manufacturing a second independent vector for a defective matrix.
    """
    if name not in {"Eigenvalues", "Eigenvectors", "MatrixExp"} or len(args) != 1:
        raise ValueError("La operación espectral requiere exactamente una matriz.")
    matrix = _matrix(args[0])
    floats = matrix.atoms(sp.Float)
    precision = min((item._prec for item in floats), default=None)
    digits = max(2, int(precision * 0.30103)) if precision else None
    if digits and digits > 80:
        raise ValueError("El presupuesto espectral decimal admite hasta 80 dígitos de entrada.")
    exact = matrix.xreplace({item: sp.Rational(item) for item in floats})
    requirements = _requirements(matrix, assumptions)
    warnings = []
    details = {
        "operation": name, "method": "sympy.Matrix", "sympy_version": sp.__version__,
        "shape": list(matrix.shape), "domain_analysis": "partial",
        "precision_certified": False, "input_operations": sum(int(sp.count_ops(item)) for item in matrix),
        "complexity": "symbolic characteristic roots or Jordan form; dimension <= 4",
    }
    if floats:
        warnings.append("Los decimales se tratan como sus valores binarios almacenados; la incertidumbre de entrada y los dígitos correctos no están certificados.")
        details.update(input_precision_bits=precision, evaluation_digits=digits,
                       float_policy="exact_binary_rationals_then_evalf")
    try:
        if name == "MatrixExp":
            value = exact.exp().applyfunc(sp.simplify).as_immutable()
            details["method"] = "sympy.Matrix.exp"
        elif name == "Eigenvalues":
            eigenvalues = exact.eigenvals(error_when_incomplete=True)
            if sum(eigenvalues.values()) != exact.rows:
                raise ValueError("No se obtuvo el espectro completo dentro del presupuesto.")
            value = sp.Tuple(*(eigenvalue for eigenvalue in sorted(eigenvalues, key=sp.default_sort_key)
                               for _ in range(eigenvalues[eigenvalue])))
            details.update(method="sympy.Matrix.eigenvals", ordering="sympy.default_sort_key",
                           multiplicity="algebraic")
        else:
            diagonal = tuple(exact[index, index] for index in range(exact.rows))
            undecided_diagonal_multiplicities = exact.is_diagonal() and any(
                (left - right).is_zero is None for left, right in combinations(diagonal, 2))
            if undecided_diagonal_multiplicities:
                # Coordinate unit vectors remain an eigenbasis even when diagonal
                # values coincide. Do not exclude that valid exceptional point.
                groups = [(diagonal[index], 1, [sp.eye(exact.rows)[:, index]])
                          for index in sorted(range(exact.rows), key=lambda index: sp.default_sort_key(diagonal[index]))]
            else:
                groups = sorted(exact.eigenvects(error_when_incomplete=True), key=lambda group: sp.default_sort_key(group[0]))
            if sum(multiplicity for _, multiplicity, _ in groups) != exact.rows:
                raise ValueError("No se obtuvieron todos los espacios propios.")
            vectors = []
            paired = []
            algebraic = []
            geometric = []
            for eigenvalue, multiplicity, basis in groups:
                if not basis:
                    raise ValueError("No se pudo calcular una base de un espacio propio.")
                rank = exact.rows - len(basis)
                if exact.free_symbols and not undecided_diagonal_multiplicities:
                    requirements.extend(condition for condition in _rank_requirement(
                        exact - eigenvalue * sp.eye(exact.rows), rank, assumptions)
                                        if condition not in requirements)
                for vector in basis:
                    if vector.is_zero_matrix is True:
                        raise ValueError("El cálculo espectral produjo un vector nulo.")
                    residual = (exact * vector - eigenvalue * vector).applyfunc(sp.simplify)
                    if residual.is_zero_matrix is not True:
                        raise ValueError("No se pudo verificar la identidad exacta del vector propio.")
                    vectors.append(sp.Tuple(*vector))
                    paired.append(eigenvalue)
                algebraic.append(int(multiplicity))
                geometric.append(len(basis))
            value = sp.Tuple(*vectors)
            complete = len(vectors) == exact.rows
            if not complete:
                warnings.append("La matriz es defectuosa en esta rama: no existe una base completa de vectores propios; se devuelven sólo los vectores independientes disponibles.")
            details.update(method="sympy.Matrix.eigenvects", ordering="grouped_by_sympy.default_sort_key",
                           vector_convention="right_column_vectors_not_normalized",
                           eigenvalues_for_vectors=[sp.sstr(item.evalf(digits) if digits else item) for item in paired],
                           algebraic_multiplicities=algebraic, geometric_multiplicities=geometric,
                           basis_complete=complete, residual_check="exact_stored_input_before_evalf")
            if undecided_diagonal_multiplicities:
                details.update(method="diagonal_coordinate_basis", ordering="sympy.default_sort_key_then_coordinate_index",
                               algebraic_multiplicities=None, geometric_multiplicities=None,
                               multiplicities_require_specialization=True)
                warnings.append("La base diagonal es válida también cuando coinciden los parámetros; las multiplicidades agrupadas requieren especializar esos parámetros.")
    except (NotImplementedError, ArithmeticError, sp.matrices.exceptions.MatrixError) as error:
        raise ValueError("El motor no pudo completar esta operación espectral dentro de su alcance.") from error
    items = _atoms(value)
    if len(items) > 64 or sum(int(sp.count_ops(item)) for item in items) > 4096:
        raise ValueError("El resultado espectral excede 64 elementos o 4096 operaciones.")
    if any(item.has(sp.nan, sp.zoo, sp.oo, -sp.oo) for item in items):
        raise ValueError("La operación espectral produjo un resultado no finito.")
    requirements.extend(condition for condition in _requirements(items, assumptions)
                        if condition not in requirements)
    if digits:
        value = _evaluate(value, digits)
        if any(item.has(sp.nan, sp.zoo, sp.oo, -sp.oo) for item in _atoms(value)):
            raise ValueError("La evaluación decimal del resultado no es finita.")
        if name == "Eigenvectors" and not matrix.free_symbols:
            # Scaled backward residuals are diagnostics, not forward-error bounds.
            atol = rtol = sp.Float(10, digits) ** (-max(1, digits - 4))
            residuals = []
            for vector, eigenvalue in zip(value, paired):
                column = sp.Matrix(vector)
                eigenvalue = eigenvalue.evalf(digits)
                residual = (matrix * column - eigenvalue * column).norm(sp.oo).evalf(digits)
                scale = (matrix.norm(sp.oo) + abs(eigenvalue)) * column.norm(sp.oo)
                if sp.Gt(residual, atol + rtol * scale) is sp.true:
                    raise ValueError("El residuo numérico de un vector propio supera la tolerancia de verificación.")
                residuals.append(sp.sstr(residual))
            details.update(residual_norm="infinity", residuals=residuals,
                           residual_absolute_tolerance=sp.sstr(atol),
                           residual_relative_tolerance=sp.sstr(rtol))
            if complete:
                columns = sp.Matrix.hstack(*(sp.Matrix(vector) for vector in value))
                try:
                    condition = (columns.norm(sp.oo) * columns.inv().norm(sp.oo)).evalf(digits)
                    details["eigenvector_condition_estimate_inf"] = sp.sstr(condition)
                    if condition.has(sp.nan, sp.zoo, sp.oo, -sp.oo) or sp.Gt(condition, 10**8) is sp.true:
                        warnings.append("La base propia está mal condicionada: un residuo pequeño no garantiza vectores ni autovalores precisos.")
                except (ValueError, ArithmeticError, sp.matrices.exceptions.MatrixError):
                    warnings.append("No se pudo estimar el condicionamiento de la base propia numérica.")
    details["requirements"] = [sp.sstr(condition) for condition in requirements]
    return OperationOutcome(value, "conditional" if requirements else "evaluated",
                            conditions=tuple(sp.sstr(condition) for condition in requirements),
                            warnings=tuple(warnings), details=details), tuple(requirements)
