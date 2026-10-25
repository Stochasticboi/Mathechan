"""Write a conservative subset of expressions using Mathechan input syntax."""

import re

import sympy as sp

from .hyperbolic import HYPERBOLIC_FUNCTIONS


class UnrepresentableExpression(ValueError):
    """The result has no supported, bounded input representation."""


FUNCTION_NAMES = {sp.sin: "Sin", sp.cos: "Cos", sp.exp: "Exp", sp.log: "Log",
                  sp.asin: "ArcSin", sp.acos: "ArcCos", sp.atan: "ArcTan",
                  **{function: name for name, function in HYPERBOLIC_FUNCTIONS.items()}}
SYMBOL_NAME = re.compile(r"[A-Za-z][A-Za-z0-9]*")


def expression_input(expression):
    """Return a candidate, or None; the kernel must still verify its roundtrip."""
    try:
        text = _write(expression, depth=0)
        return text if len(text) <= 4096 else None
    except (UnrepresentableExpression, RecursionError):
        return None


def _integer(value):
    # Reject before decimal conversion, including Python's large-int string limit.
    if abs(int(value)).bit_length() > 333:
        raise UnrepresentableExpression("Integer exceeds the input digit limit.")
    text = str(value)
    if len(text.lstrip("-")) > 100:
        raise UnrepresentableExpression("Integer exceeds the input digit limit.")
    return text


def _write(expression, depth):
    if depth > 35:
        raise UnrepresentableExpression("Expression is too deeply nested.")
    if expression is sp.I:
        return "Sqrt[-1]"
    if expression is sp.pi:
        return "Pi"
    if expression is sp.E:
        return "E"
    if isinstance(expression, sp.Symbol):
        name = expression.name
        if not SYMBOL_NAME.fullmatch(name) or name in ("Pi", "E"):
            raise UnrepresentableExpression("Unsupported or reserved symbol name.")
        if expression != sp.Symbol(name):
            raise UnrepresentableExpression("Symbol assumptions cannot be encoded.")
        return name
    if isinstance(expression, sp.Integer):
        return _integer(expression)
    if isinstance(expression, sp.Rational):
        return f"({_integer(expression.p)}/{_integer(expression.q)})"
    if len(expression.args) > 256:
        raise UnrepresentableExpression("Too many arguments.")
    write = lambda item: _write(item, depth + 1)
    from .finite_probability import FiniteDistribution
    from .joint_probability import JointFiniteDistribution
    if isinstance(expression, JointFiniteDistribution):
        result = "JointFiniteDistribution[" + write(expression.states) + "," + write(expression.probabilities) + "]"
    elif isinstance(expression, FiniteDistribution):
        result = "FiniteDistribution[" + write(expression.states) + "," + write(expression.probabilities) + "]"
    elif isinstance(expression, sp.Equality):
        result = f"({write(expression.lhs)})==({write(expression.rhs)})"
    elif isinstance(expression, sp.MatrixBase):
        result = "Matrix[{" + ",".join("{" + ",".join(write(item) for item in expression.row(row)) + "}"
                                      for row in range(expression.rows)) + "}]"
    elif isinstance(expression, sp.Tuple):
        result = "{" + ",".join(write(item) for item in expression) + "}"
    elif isinstance(expression, sp.Add):
        result = "(" + "+".join(write(item) for item in expression.args) + ")"
    elif isinstance(expression, sp.Mul):
        result = "(" + "*".join(write(item) for item in expression.args) + ")"
    elif isinstance(expression, sp.Pow):
        result = f"({write(expression.base)})^({write(expression.exp)})"
    elif expression.func in FUNCTION_NAMES and len(expression.args) == 1:
        result = f"{FUNCTION_NAMES[expression.func]}[{write(expression.args[0])}]"
    else:
        raise UnrepresentableExpression("Unsupported result function or type.")
    if len(result) > 4096:
        raise UnrepresentableExpression("Expression exceeds input length.")
    return result

