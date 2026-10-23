"""Bounded mathematical containers, held syntax, and numerical diagnostics."""

import sympy as sp
from sympy.core.symbol import Str

from .domains import require_nonzero


SEMANTIC_CALLS = frozenset({
    "Vector", "Matrix", "Hold", "ReleaseHold", "Display", "NumericError",
    "ArcSin", "ArcCos", "ArcTan", "Gamma",
})
MAX_CONTAINER_ELEMENTS = 64


def _pack(node):
    return sp.Tuple(Str(node.kind), Str(node.value), sp.Tuple(*(_pack(child) for child in node.children)))


def _unpack(value):
    from .kernel import Node

    return Node(str(value[0]), str(value[1]), tuple(_unpack(child) for child in value[2]))


def _source(node):
    if node.kind in {"name", "number"}:
        return node.value
    if node.kind == "list":
        return "{" + ",".join(_source(child) for child in node.children) + "}"
    if node.kind == "call":
        return node.value + "[" + ",".join(_source(child) for child in node.children) + "]"
    if node.kind == "pattern":
        return node.value + "_" + (node.children[0].value if node.children[0].value != "Scalar" else "")
    if node.kind == "unary":
        return "(" + node.value + _source(node.children[0]) + ")"
    if node.kind == "binary":
        return "(" + _source(node.children[0]) + node.value + _source(node.children[1]) + ")"
    raise ValueError("La construcción retenida no pertenece al lenguaje de expresiones.")


class HeldExpression(sp.Basic):
    """An inert, immutable syntax tree; its strings never enter sympify or eval."""

    @classmethod
    def from_node(cls, node):
        return cls(_pack(node))

    @property
    def node(self):
        return _unpack(self.args[0])

    def _sympystr(self, printer):
        return "Hold[" + _source(self.node) + "]"

    def _latex(self, printer):
        text = _source(self.node).replace("{", r"\{").replace("}", r"\}")
        return r"\operatorname{Hold}\left[\text{" + text + r"}\right]"


def _arity(node, count):
    if len(node.children) != count:
        raise ValueError(f"{node.value} requiere exactamente {count} argumento(s).")


def _scalar(value):
    if not isinstance(value, sp.Expr) or value.is_commutative is not True:
        raise ValueError("Se requiere una expresión escalar conmutativa.")
    return value


def _digits(value, maximum=1000):
    if not isinstance(value, sp.Integer) or not 1 <= value <= maximum:
        raise ValueError(f"La precisión debe ser un entero entre 1 y {maximum}.")
    return int(value)


def track_function_domain(name, argument, restrictions, state):
    """Track necessary exclusions and principal branches, without imposing reals."""
    if name == "Log":
        if argument.is_zero is True:
            raise ValueError("Log no está definido en cero.")
        require_nonzero(argument, restrictions)
    if name in {"Log", "Sqrt", "ArcSin", "ArcCos", "ArcTan"} and argument.free_symbols:
        state.warnings.append(
            f"{name} usa la rama principal compleja; el seguimiento de cortes de rama es parcial."
        )
    if name == "ArcTan":
        excluded = 1 + argument ** 2
        if excluded.is_zero is True:
            raise ValueError("ArcTan no es finito en los puntos +i y -i.")
        require_nonzero(excluded, restrictions)
    if name == "Gamma":
        if argument.is_integer is True and argument.is_nonpositive is True:
            raise ValueError("Gamma tiene polos en los enteros no positivos.")
        if not (argument.is_integer is False or argument.is_positive is True):
            requirement = sp.Not(sp.Contains(argument, sp.Complement(sp.S.Integers, sp.S.Naturals)))
            if requirement not in state.requirements:
                state.requirements.append(requirement)
            state.conditions.append(f"({sp.sstr(argument)}) no es un entero no positivo")
            state.mark_status("conditional")
        state.warnings.append("El seguimiento de los polos de Gamma es parcial.")


def semantic_call(node, build, restrictions, state, bindings=None, functions=None, definitions=None):
    """Evaluate one bounded type or diagnostic using the caller's lexical context."""
    bindings = {} if bindings is None else bindings
    functions = {} if functions is None else functions
    definitions = {} if definitions is None else definitions

    def read(child):
        return build(child, restrictions, state, bindings, functions, definitions)

    name = node.value
    if name == "Hold":
        _arity(node, 1)
        return HeldExpression.from_node(node.children[0])
    if name == "ReleaseHold":
        _arity(node, 1)
        held = read(node.children[0])
        if not isinstance(held, HeldExpression):
            raise ValueError("ReleaseHold requiere una expresión Hold.")
        return read(held.node)
    if name in {"Vector", "Matrix"}:
        _arity(node, 1)
        container = node.children[0]
        if container.kind != "list" or not container.children:
            raise ValueError(f"{name} requiere una lista no vacía.")
        if name == "Vector":
            rows = tuple((item,) for item in container.children)
        else:
            if any(row.kind != "list" or not row.children for row in container.children):
                raise ValueError("Matrix requiere una lista de filas no vacías.")
            rows = tuple(row.children for row in container.children)
            if len({len(row) for row in rows}) != 1:
                raise ValueError("Las filas de Matrix deben tener la misma longitud.")
        if sum(len(row) for row in rows) > MAX_CONTAINER_ELEMENTS:
            raise ValueError("Vector y Matrix admiten hasta 64 elementos escalares.")
        values = [[_scalar(read(item)) for item in row] for row in rows]
        return sp.ImmutableMatrix(values)
    if name == "Display":
        _arity(node, 2)
        digits = _digits(read(node.children[1]))
        value = _scalar(read(node.children[0]))
        state.details["presentation"] = {"digits": digits, "text": sp.sstr(value.evalf(digits))}
        return value
    if name == "NumericError":
        _arity(node, 2)
        digits = _digits(read(node.children[1]), maximum=990)
        value = _scalar(read(node.children[0]))
        if value.is_number is not True or value.is_finite is not True:
            raise ValueError("NumericError requiere un escalar numérico finito sin parámetros libres.")
        low, high = value.evalf(digits), value.evalf(digits + 10)
        if any(item.is_finite is not True for item in (low, high)):
            raise ValueError("No se obtuvo una evaluación numérica finita para estimar el error.")
        estimate = sp.Abs(high - low).evalf(digits + 10)
        state.details["numeric_error"] = {
            "method": "precision_comparison", "digits": digits,
            "comparison_digits": digits + 10, "absolute_difference": sp.sstr(estimate),
            "certified_bound": False,
        }
        state.warnings.append(
            "NumericError compara dos precisiones: es una estimación, no una cota certificada "
            "ni una medida del error de los datos de entrada."
        )
        if value.has(sp.Float):
            state.warnings.append("Aumentar la precisión no recupera dígitos perdidos en valores aproximados de entrada.")
        return estimate
    if name in {"ArcSin", "ArcCos", "ArcTan", "Gamma"}:
        _arity(node, 1)
        argument = _scalar(read(node.children[0]))
        track_function_domain(name, argument, restrictions, state)
        return {"ArcSin": sp.asin, "ArcCos": sp.acos, "ArcTan": sp.atan, "Gamma": sp.gamma}[name](argument)
    raise ValueError(f"Operación semántica no admitida: {name}.")
