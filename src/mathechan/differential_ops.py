"""Bounded formal derivatives and Cartesian vector differential operators."""

import sympy as sp

from .calculus import OperationOutcome

MAX_INPUT_OPERATIONS = 256
MAX_OUTPUT_OPERATIONS = 4096
MAX_VARIABLES = 8
MAX_DERIVATIVE_ORDER = 32


def _scalar(expression):
    if (not isinstance(expression, sp.Expr)
            or expression.is_commutative is not True
            or expression.has(sp.nan, sp.zoo, sp.oo, -sp.oo)):
        raise ValueError("Se requiere una expresión escalar finita.")
    return expression


def _variables(variables):
    if not isinstance(variables, (list, tuple, sp.Tuple)):
        raise ValueError("Las variables deben formar una lista de símbolos distintos.")
    items = tuple(variables)
    if (not 1 <= len(items) <= MAX_VARIABLES
            or any(not isinstance(item, sp.Symbol) for item in items)
            or len(set(items)) != len(items)):
        raise ValueError("Se requieren entre una y ocho variables distintas.")
    return items


def _budget(expressions, variables):
    symbols = set(variables)
    operations = 0
    for expression in expressions:
        symbols.update(expression.free_symbols)
        operations += int(sp.count_ops(expression))
    if len(symbols) > MAX_VARIABLES or operations > MAX_INPUT_OPERATIONS:
        raise ValueError("El cálculo diferencial admite 256 operaciones y ocho símbolos como máximo.")


def _outcome(value, operation, expressions, variables, **details):
    items = list(value) if isinstance(value, sp.MatrixBase) else [value]
    if len(items) > 64 or sum(int(sp.count_ops(item)) for item in items) > MAX_OUTPUT_OPERATIONS:
        raise ValueError("El resultado diferencial excede 64 elementos o 4096 operaciones.")
    unresolved = any(item.has(sp.Derivative) for item in items)
    warnings = []
    if unresolved:
        warnings.append("El resultado conserva derivadas formales sin evaluar.")
    # Derivation is formal. In particular, a generic complex symbol must not
    # silently become real to differentiate Abs, conjugate or re/im.
    return OperationOutcome(
        value,
        "unresolved" if unresolved else "evaluated",
        warnings=tuple(warnings),
        details={
            "method": "sympy.diff",
            "operation": operation,
            "sympy_version": sp.__version__,
            "variables": [sp.sstr(item) for item in variables],
            "domain_analysis": "partial",
            "differentiability": "not_certified",
            "input_operations": sum(int(sp.count_ops(item)) for item in expressions),
            **details,
        },
    )


def derivative_expression(expr, specs):
    """Apply ordered partial derivatives; each order and the total are <= 32."""
    expr = _scalar(expr)
    if not isinstance(specs, (list, tuple, sp.Tuple)) or not specs:
        raise ValueError("D requiere al menos una especificación de derivación.")
    normalized = []
    total = 0
    for spec in specs:
        if not isinstance(spec, (list, tuple, sp.Tuple)) or len(spec) != 2:
            raise ValueError("Cada derivada requiere un símbolo y un orden entero.")
        variable, order = spec
        if (not isinstance(variable, sp.Symbol) or isinstance(order, bool)
                or not isinstance(order, (int, sp.Integer))
                or not 1 <= order <= MAX_DERIVATIVE_ORDER):
            raise ValueError("Cada orden de derivación debe ser un entero entre 1 y 32.")
        total += int(order)
        normalized.append((variable, int(order)))
    if total > MAX_DERIVATIVE_ORDER:
        raise ValueError("El orden total de derivación no puede superar 32.")
    variables = tuple(dict.fromkeys(variable for variable, _ in normalized))
    _budget([expr], variables)
    # Evaluate in the supplied order; commutation of mixed derivatives is not
    # separately asserted for nonsmooth expressions.
    value = expr
    for variable, order in normalized:
        for _ in range(order):
            value = sp.diff(value, variable)
            if int(sp.count_ops(value)) > MAX_OUTPUT_OPERATIONS:
                raise ValueError("La derivada excede el límite de 4096 operaciones.")
    return _outcome(value, "D", [expr], variables, orders=[order for _, order in normalized])


def _vector(expression):
    if isinstance(expression, sp.MatrixBase):
        if expression.cols != 1:
            raise ValueError("Se requiere un vector columna, no una matriz general.")
        items = tuple(expression)
    elif isinstance(expression, (list, tuple, sp.Tuple)):
        items = tuple(expression)
    else:
        raise ValueError("Se requiere una lista o un vector columna.")
    if not 1 <= len(items) <= MAX_VARIABLES:
        raise ValueError("El vector debe contener entre uno y ocho elementos.")
    return tuple(_scalar(item) for item in items)


def vector_expression(operation, expr, variables):
    """Cartesian operators only; these functions do not provide matrix algebra."""
    variables = _variables(variables)
    if operation not in {"Grad", "Div", "Curl", "Jacobian", "Hessian"}:
        raise ValueError("Operador diferencial vectorial desconocido.")
    scalar_operation = operation in {"Grad", "Hessian"}
    expressions = (_scalar(expr),) if scalar_operation else _vector(expr)
    _budget(expressions, variables)
    dimension = len(variables)
    if operation in {"Div", "Curl"} and len(expressions) != dimension:
        raise ValueError("El campo debe tener tantas componentes como coordenadas.")
    if operation == "Curl" and dimension != 3:
        raise ValueError("Curl requiere exactamente tres coordenadas cartesianas.")
    if operation == "Grad":
        value = sp.ImmutableMatrix([sp.diff(expr, variable) for variable in variables])
    elif operation == "Hessian":
        value = sp.ImmutableMatrix(sp.hessian(expr, variables))
    elif operation == "Div":
        value = sum((sp.diff(component, variable)
                     for component, variable in zip(expressions, variables)), sp.S.Zero)
    elif operation == "Jacobian":
        value = sp.ImmutableMatrix(expressions).jacobian(variables).as_immutable()
    else:
        x, y, z = variables
        first, second, third = expressions
        value = sp.ImmutableMatrix([
            sp.diff(third, y) - sp.diff(second, z),
            sp.diff(first, z) - sp.diff(third, x),
            sp.diff(second, x) - sp.diff(first, y),
        ])
    return _outcome(value, operation, expressions, variables, coordinates="Cartesian")
