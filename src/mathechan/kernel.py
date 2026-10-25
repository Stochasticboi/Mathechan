"""Parser acotado y evaluación explícita sobre objetos SymPy."""

import math
import re
from dataclasses import dataclass, field
from fractions import Fraction
from html import escape

import sympy as sp

from .domains import condition_text, require_nonzero, restrictions_at
from .language_ops import SCIENTIFIC_CALLS, EvaluationState, scientific_call
from .printer import expression_input
from .assumptions import ASSUMPTION_CALLS, assumption_call, refine_expression, validate_assumptions
from .definitions import DeferredDefinition, DeferredFunction, StoredDefinition, UserFunction
from .semantic_types import SEMANTIC_CALLS, HeldExpression, semantic_call, track_function_domain
from .hyperbolic import HYPERBOLIC_FUNCTIONS, track_hyperbolic_domain


class MathechanError(ValueError):
    """Entrada fuera del lenguaje experimental o del dominio admitido."""


@dataclass(frozen=True)
class Node:
    kind: str
    value: str
    children: tuple = ()


@dataclass(frozen=True)
class EvaluationResult:
    kind: str
    text: str
    latex: str = ""
    svg: str = ""
    points: tuple = ()
    input: str | None = None
    conditions: tuple = ()
    warnings: tuple = ()
    status: str = "evaluated"
    exact: bool = True
    details: dict = field(default_factory=dict)

    def to_dict(self):
        """Devuelve contenido serializable para una interfaz futura."""
        result = {"kind": self.kind, "text": self.text, "input": self.input,
                  "conditions": list(self.conditions), "warnings": list(self.warnings),
                  "status": self.status, "exact": self.exact, "details": self.details}
        if self.latex:
            result["latex"] = self.latex
        if self.svg:
            result["svg"] = self.svg
            result["points"] = [list(point) for point in self.points]
        return result


TOKEN = re.compile(r'\s*(?:(\d+(?:\.\d+)?)|([A-Za-z][A-Za-z0-9]*)|("[A-Za-z][A-Za-z0-9]*")|(/\.|->|:>|==|!=|<=|>=|[.<>=+*/^(),\[\]{}_-]))')


class Parser:
    def __init__(self, source, allow_assignment=False):
        if not isinstance(source, str) or not source.strip():
            raise MathechanError("La entrada debe ser texto no vacío.")
        if len(source) > 4096:
            raise MathechanError("Entrada demasiado larga (máximo 4096 caracteres).")
        self.tokens = []
        position = 0
        source = source.strip()
        while position < len(source):
            match = TOKEN.match(source, position)
            if match is None:
                raise MathechanError(f"Carácter no admitido en posición {position + 1}.")
            self.tokens.append(next(value for value in match.groups() if value is not None))
            position = match.end()
        if len(self.tokens) > 256:
            raise MathechanError("Demasiados elementos (máximo 256).")
        self.index = 0
        self.depth = 0
        self.allow_assignment = allow_assignment

    def peek(self):
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def take(self, expected=None):
        token = self.peek()
        if token is None or (expected is not None and token != expected):
            raise MathechanError(f"Se esperaba {expected or 'una expresión'}.")
        self.index += 1
        return token

    def parse(self):
        if (self.allow_assignment and len(self.tokens) >= 2
                and self.tokens[0][0].isalpha() and self.tokens[1] == "="):
            name = self.take()
            self.take("=")
            node = Node("assignment", name, (self.expression(),))
        else:
            node = self.expression()
        if self.peek() is not None:
            raise MathechanError(f"Elemento inesperado: {self.peek()}.")
        return node

    def expression(self, minimum=0):
        self.depth += 1
        if self.depth > 40:
            raise MathechanError("Anidación excesiva (máximo 40).")
        token = self.take()
        if token in ("+", "-"):
            left = Node("unary", token, (self.expression(25),))
        elif token == "(":
            left = self.expression()
            self.take(")")
        elif token == "{":
            left = Node("list", "", self.arguments("}"))
        elif token[0].isdigit():
            if len(token) > 100:
                raise MathechanError("Número demasiado largo (máximo 100 caracteres).")
            left = Node("number", token)
        elif token.startswith('"'):
            if token[1:-1] not in ("Cartesian", "Cylindrical", "Spherical", "Components", "Orthonormal"):
                raise MathechanError("Los textos sólo se admiten como opciones de coordenadas conocidas.")
            left = Node("string", token[1:-1])
        elif token[0].isalpha():
            if self.peek() == "_":
                self.take("_")
                kind = self.take() if self.peek() in ("Integer", "Real", "Scalar") else "Scalar"
                left = Node("pattern", token, (Node("name", kind),))
            elif self.peek() == "[":
                self.take("[")
                left = Node("call", token, self.arguments("]"))
            else:
                left = Node("name", token)
        else:
            raise MathechanError(f"Inicio de expresión no admitido: {token}.")
        comparisons = {"==", "!=", "<", "<=", ">", ">="}
        precedence = {"/.": 2, "->": 3, ":>": 3, **dict.fromkeys(comparisons, 5), "+": 10, "-": 10, "*": 20, "/": 20, ".": 22, "^": 30}
        while self.peek() in precedence and precedence[self.peek()] >= minimum:
            operator = self.take()
            binding = precedence[operator]
            right = self.expression(binding if operator in ("^", "->", ":>") else binding + 1)
            if operator in comparisons and ((left.kind == "binary" and left.value in comparisons)
                                      or (right.kind == "binary" and right.value in comparisons)):
                raise MathechanError("No se admiten cadenas de comparaciones; use And o una lista.")
            if operator == ".":
                left = Node("call", "Dot", (left, right))
            elif operator in ("/.", "->", ":>"):
                left = Node("call", {"/.": "ReplaceAll", "->": "Rule", ":>": "RuleDelayed"}[operator], (left, right))
            else:
                left = Node("binary", operator, (left, right))
        self.depth -= 1
        return left

    def arguments(self, closing):
        arguments = []
        if self.peek() != closing:
            while True:
                arguments.append(self.expression())
                if self.peek() != ",":
                    break
                self.take(",")
        self.take(closing)
        return tuple(arguments)


FUNCTIONS = {
    **HYPERBOLIC_FUNCTIONS,
    "Sin": sp.sin, "Cos": sp.cos, "Exp": sp.exp, "Log": sp.log,
    "Sqrt": sp.sqrt, "Abs": sp.Abs, "Expand": sp.expand, "Simplify": sp.simplify,
}


def _stored_value(stored, replacements, restrictions, state):
    """Use immutable snapshots while carrying their original domain conditions."""
    value = stored.value.xreplace(replacements)
    if value.has(sp.Order) or any("aproximación truncada" in warning for warning in stored.warnings):
        state.mark_status("series")
    for item in stored.restrictions:
        transformed = item.xreplace(replacements)
        if transformed.is_zero is True or transformed.has(sp.zoo, sp.nan):
            raise MathechanError("El valor viola una restricción de la definición original.")
        require_nonzero(transformed, restrictions)
    for item in stored.requirements:
        transformed = sp.simplify(item.xreplace(replacements))
        if transformed is sp.false:
            raise MathechanError("El valor viola una condición de la definición original.")
        if transformed is not sp.true:
            state.requirements.append(transformed)
            state.conditions.append(sp.sstr(transformed))
            state.mark_status("conditional")
    state.warnings.extend(stored.warnings)
    return value


def build(node, restrictions=None, state=None, bindings=None, functions=None, definitions=None):
    """Traduce nodos propios; nunca interpreta cadenas como código."""
    state = EvaluationState() if state is None else state
    bindings = {} if bindings is None else bindings
    functions = {} if functions is None else functions
    definitions = {} if definitions is None else definitions
    restrictions = [] if restrictions is None else restrictions
    state.steps += 1
    if state.steps > 10000:
        raise MathechanError("La evaluación excede el presupuesto de 10000 pasos.")

    def read(child):
        return build(child, restrictions, state, bindings, functions, definitions)

    def deferred(body, scope):
        if state.call_depth >= 32:
            raise MathechanError("La evaluación diferida excede 32 llamadas anidadas.")
        state.call_depth += 1
        try:
            return build(body, restrictions, state, scope, functions, definitions)
        finally:
            state.call_depth -= 1

    if node.kind == "number":
        rational = Fraction(node.value)
        return sp.Rational(rational.numerator, rational.denominator)
    if node.kind == "name":
        if node.value in bindings:
            return bindings[node.value]
        if node.value in definitions:
            value = definitions[node.value]
            if isinstance(value, DeferredDefinition):
                materialized = deferred(value.node, bindings)
                if isinstance(materialized, sp.Expr) and materialized.is_number is True:
                    validate_assumptions(state.assumptions.subs(sp.Symbol(node.value), materialized))
                return materialized
            if isinstance(value, DeferredFunction):
                raise MathechanError("La función diferida requiere argumentos entre corchetes.")
            if isinstance(value, StoredDefinition):
                return _stored_value(value, {sp.Symbol(name): item for name, item in bindings.items()}, restrictions, state)
            if isinstance(value, UserFunction):
                raise MathechanError("La función definida requiere argumentos entre corchetes.")
            return value
        return {"Pi": sp.pi, "E": sp.E, "Infinity": sp.oo, "True": sp.true,
                "False": sp.false, "Reals": sp.S.Reals, "Complexes": sp.S.Complexes,
                "Integers": sp.S.Integers}.get(node.value, sp.Symbol(node.value))
    if node.kind == "list":
        if len(node.children) > 64:
            raise MathechanError("Una lista admite hasta 64 elementos en este lenguaje experimental.")
        return sp.Tuple(*(read(child) for child in node.children))
    if node.kind == "unary":
        value = read(node.children[0])
        if isinstance(value, (sp.MatrixBase, sp.Tuple)):
            from .matrix_language import matrix_binary
            return matrix_binary("*", sp.S.One if node.value == "+" else -sp.S.One, value, state)
        if not isinstance(value, sp.Expr):
            raise MathechanError("Los signos requieren una expresión escalar.")
        return value if node.value == "+" else -value
    if node.kind == "binary":
        left, right = (read(child) for child in node.children)
        if isinstance(left, (sp.MatrixBase, sp.Tuple)) or isinstance(right, (sp.MatrixBase, sp.Tuple)):
            from .matrix_language import matrix_binary
            return matrix_binary(node.value, left, right, state)
        if not isinstance(left, sp.Expr) or not isinstance(right, sp.Expr):
            raise MathechanError("Los operadores requieren expresiones escalares.")
        if node.value == "==":
            return sp.Eq(left, right, evaluate=False)
        if node.value in ("!=", "<", "<=", ">", ">="):
            constructor = {"!=": sp.Ne, "<": sp.Lt, "<=": sp.Le, ">": sp.Gt, ">=": sp.Ge}[node.value]
            return constructor(left, right)
        if node.value == "+":
            return left + right
        if node.value == "-":
            return left - right
        if node.value == "*":
            return left * right
        if node.value == "/":
            if right == 0:
                raise MathechanError("División por cero.")
            require_nonzero(right, restrictions)
            return left / right
        if right.is_number and (right.is_real is not True or abs(right) > 1000):
            raise MathechanError("Exponente numérico fuera del límite experimental ±1000.")
        if right.is_negative is True:
            require_nonzero(left, restrictions)
        return left ** right
    if node.kind == "call":
        if node.value in ("Rule", "RuleDelayed", "ReplaceAll") or (node.value == "Substitute" and len(node.children) == 2):
            from .replacement import replacement_call
            return replacement_call(node, build, restrictions, state, bindings, functions, definitions)
        if node.value == "If":
            if len(node.children) != 3:
                raise MathechanError("Use If[condición,verdadero,falso].")
            condition = sp.simplify(read(node.children[0]))
            if condition is sp.true:
                return read(node.children[1])
            if condition is sp.false:
                return read(node.children[2])
            from sympy.logic.boolalg import Boolean
            if not isinstance(condition, Boolean):
                raise MathechanError("If requiere una condición lógica.")
            state.mark_status("unresolved")
            state.warnings.append("If conserva sus ramas sin evaluar porque la condición no se pudo decidir.")
            return HeldExpression.from_node(node)
        if node.value in ASSUMPTION_CALLS or (node.value == "Simplify" and len(node.children) == 2):
            return assumption_call(node, build, restrictions, state, bindings, functions, definitions)
        if node.value in SEMANTIC_CALLS:
            return semantic_call(node, build, restrictions, state, bindings, functions, definitions)
        if node.value in SCIENTIFIC_CALLS:
            return scientific_call(node, build, restrictions, state, bindings, functions, definitions)
        if isinstance(definitions.get(node.value), DeferredFunction):
            function = definitions[node.value]
            if len(node.children) != len(function.parameters):
                raise MathechanError("La función diferida recibió un número incorrecto de argumentos.")
            arguments = [read(child) for child in node.children]
            for pattern, argument in zip(function.patterns or ("ScalarPattern",) * len(arguments), arguments):
                matches = (isinstance(argument, sp.Expr) and argument.is_commutative is True
                           and (pattern == "ScalarPattern" or
                                pattern == "IntegerPattern" and argument.is_integer is True or
                                pattern == "RealPattern" and argument.is_real is True))
                if not matches:
                    raise MathechanError("Un argumento no cumple el patrón declarado de la función.")
            scope = {**bindings, **dict(zip(function.parameters, arguments))}
            return deferred(function.node, scope)
        if isinstance(definitions.get(node.value), UserFunction):
            function = definitions[node.value]
            if len(node.children) != len(function.parameters):
                raise MathechanError("La función definida recibió un número incorrecto de argumentos.")
            arguments = [read(child) for child in node.children]
            if any(not isinstance(value, sp.Expr) for value in arguments):
                raise MathechanError("Los argumentos de una función definida deben ser escalares.")
            return _stored_value(function.body, dict(zip(function.parameters, arguments)), restrictions, state)
        if node.value in functions:
            if len(node.children) != 1:
                raise MathechanError("La función dependiente de DSolve requiere un argumento.")
            argument = read(node.children[0])
            if not isinstance(argument, sp.Expr):
                raise MathechanError("La función dependiente requiere un argumento escalar.")
            return functions[node.value](argument)
        if node.value not in FUNCTIONS:
            raise MathechanError(f"Función no admitida: {node.value}.")
        if len(node.children) != 1:
            raise MathechanError(f"{node.value} requiere exactamente un argumento.")
        argument = read(node.children[0])
        if not isinstance(argument, sp.Expr):
            raise MathechanError("La función requiere un argumento escalar.")
        if node.value in ("Log", "Sqrt"):
            track_function_domain(node.value, argument, restrictions, state)
        elif node.value in HYPERBOLIC_FUNCTIONS:
            track_hyperbolic_domain(node.value, argument, restrictions, state)
        argument = refine_expression(argument, getattr(state, "assumptions", sp.true))
        return refine_expression(FUNCTIONS[node.value](argument), getattr(state, "assumptions", sp.true))
    raise MathechanError("Construcción no admitida por el evaluador.")


def plot(node, source=None, state=None, definitions=None):
    if len(node.children) != 2:
        raise MathechanError("Use Plot[expresión, {variable, mínimo, máximo}].")
    range_node = node.children[1]
    if range_node.kind != "list" or len(range_node.children) != 3:
        raise MathechanError("Plot requiere un rango {variable, mínimo, máximo}.")
    restrictions = []
    state = EvaluationState() if state is None else state
    definitions = {} if definitions is None else definitions
    variable = build(range_node.children[0], restrictions, state)
    local_definitions = {name: value for name, value in definitions.items() if name != str(variable)}
    expression = build(node.children[0], restrictions, state, definitions=local_definitions)
    lower, upper = (build(child, restrictions, state, definitions=definitions)
                    for child in range_node.children[1:])
    if not isinstance(expression, sp.Expr) or not all(isinstance(item, sp.Expr) for item in (lower, upper)):
        raise MathechanError("Plot requiere una expresión y extremos escalares.")
    if not isinstance(variable, sp.Symbol) or expression.free_symbols - {variable}:
        raise MathechanError("Plot requiere una sola variable libre y un símbolo como variable.")
    if any(item.free_symbols - {variable} for item in restrictions):
        raise MathechanError("Plot no puede comprobar condiciones con variables adicionales.")
    parameters = {}
    for name, stored in definitions.items():
        value = stored.value if isinstance(stored, StoredDefinition) else stored
        if name != str(variable) and isinstance(value, sp.Expr) and value.is_number is True:
            parameters[sp.Symbol(name)] = value
    requirements = [item.subs(parameters, simultaneous=True) for item in state.requirements]
    if any(bound.is_real is not True or bound.is_finite is not True for bound in (lower, upper)):
        raise MathechanError("Los extremos deben ser reales finitos.")
    low, high = float(lower), float(upper)
    if not math.isfinite(low) or not math.isfinite(high) or not math.isfinite(high - low) or low >= high:
        raise MathechanError("El rango debe ser finito y estrictamente creciente.")
    points = []
    constant_value = expression.evalf() if expression.is_number else None
    for index in range(201):
        fraction = index / 200
        x = low if index == 0 else high if index == 200 else low + (high - low) * fraction
        if not math.isfinite(x):
            raise MathechanError("Una muestra del rango excedió el rango numérico admitido.")
        sample = sp.Float(x)
        domain_sample = lower if index == 0 else upper if index == 200 else sample
        coordinate = x if 0 < index < 200 else None
        diagnostic = restrictions_at(restrictions, variable, domain_sample, coordinate)
        if diagnostic:
            raise MathechanError(f"{diagnostic} cerca de {x:g}.")
        for requirement in requirements:
            checked = sp.simplify(requirement.subs(variable, domain_sample))
            if checked is not sp.true:
                raise MathechanError(
                    f"Plot no puede verificar una hipótesis o condición original cerca de {x:g}."
                )
        value = constant_value if constant_value is not None else expression.subs(variable, sample)
        if not isinstance(value, (sp.Float, sp.Rational)):
            value = value.evalf()
        if value.is_real is not True or value.is_finite is not True:
            raise MathechanError(f"Plot encontró un valor fuera del dominio real finito cerca de {x:g}.")
        y = float(value)
        if not math.isfinite(y):
            raise MathechanError("Plot excedió el rango numérico admitido.")
        points.append((x, y))
    minimum, maximum = min(y for _, y in points), max(y for _, y in points)
    span = maximum - minimum
    if not math.isfinite(span):
        raise MathechanError("La amplitud del gráfico excede el rango numérico admitido.")
    padding = span * 0.05 if span else max(abs(minimum) * 0.05, 1.0)
    minimum, maximum = minimum - padding, maximum + padding
    if not math.isfinite(minimum) or not math.isfinite(maximum) or not math.isfinite(maximum - minimum):
        raise MathechanError("La escala del gráfico excede el rango numérico admitido.")
    coordinates = []
    for x, y in points:
        horizontal = 40 + 560 * ((x - low) / (high - low))
        vertical = 280 - 240 * ((y - minimum) / (maximum - minimum))
        if not math.isfinite(horizontal) or not math.isfinite(vertical):
            raise MathechanError("Una coordenada SVG excedió el rango numérico admitido.")
        coordinates.append(f"{horizontal:.3f},{vertical:.3f}")
    coordinates = " ".join(coordinates)
    title = escape(f"{sp.sstr(expression)}; {variable} ∈ [{low:g}, {high:g}]")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="340" viewBox="0 0 640 340" role="img">'
           f'<title>{title}</title><rect width="640" height="340" fill="white"/>'
           '<path d="M40 40 V280 H600" fill="none" stroke="#475569"/>'
           f'<polyline points="{coordinates}" fill="none" stroke="#2563eb" stroke-width="2"/>'
           f'<text x="40" y="315" font-size="13">{title}</text></svg>')
    if definitions:
        source = None
        state.warnings.append("El gráfico no ofrece entrada reutilizable independiente del contexto de sesión.")
    return EvaluationResult("plot", sp.sstr(expression), svg=svg, points=tuple(points),
                            input=source, conditions=condition_text(restrictions) + tuple(state.conditions),
                            warnings=tuple(dict.fromkeys(state.warnings)), status=state.status,
                            exact=False, details=state.details)


def reusable_input(expression):
    """Accept a candidate only after bounded parse/build and structural equality."""
    candidate = expression_input(expression)
    if candidate is None:
        return None
    try:
        rebuilt = build(Parser(candidate).parse())
        return candidate if rebuilt == expression else None
    except (MathechanError, ArithmeticError, TypeError, ValueError, RecursionError):
        return None


def _evaluate_node(node, source, definitions=None, assumptions=None, capture=None):
    """Return structured output and its immutable value without reparsing display text."""
    try:
        state = EvaluationState()
        state.assumptions = validate_assumptions(sp.true if assumptions is None else assumptions)
        if state.assumptions is not sp.true:
            state.conditions.append(sp.sstr(state.assumptions))
            state.requirements.append(state.assumptions)
            state.mark_status("conditional")
        if node.kind == "call" and node.value == "Plot":
            return plot(node, source.strip(), state, definitions), None
        restrictions = []
        expression = build(node, restrictions, state, definitions=definitions)
        expression = refine_expression(expression, state.assumptions)
        if expression.has(sp.Order):
            state.mark_status("series")
        if capture is not None:
            capture.update(restrictions=tuple(restrictions), requirements=tuple(state.requirements), warnings=tuple(state.warnings))
        if ((expression.has(sp.zoo, sp.nan) and not expression.has(sp.Piecewise))
                or (isinstance(expression, sp.Expr) and expression.is_finite is False)):
            raise MathechanError("El resultado no es finito o está indefinido.")
        candidate = reusable_input(expression)
        warnings = list(state.warnings)
        if candidate is None:
            warnings.append("El resultado no tiene entrada reutilizable dentro del lenguaje y límites actuales.")
        if restrictions:
            warnings.append("La entrada del resultado no conserva por sí sola las condiciones originales; consérvelas por separado.")
        exact = not expression.has(sp.Float)
        kind = "solutions" if node.kind == "call" and node.value in ("Solve", "NSolve", "DSolve") else "expression"
        if isinstance(expression, sp.Equality) and kind == "expression":
            kind = "equation"
        elif isinstance(expression, sp.Tuple):
            kind = "list"
        elif isinstance(expression, sp.ImmutableMatrix):
            kind = "matrix"
        elif isinstance(expression, HeldExpression):
            kind = "held"
        elif expression.func.__name__ in {"FiniteDistribution", "JointFiniteDistribution"}:
            kind = "distribution"
        elif expression.func.__name__ == "RuleValue":
            kind = "rule"
        elif isinstance(expression, sp.core.relational.Relational) and kind == "expression":
            kind = "inequality"
        elif expression in (sp.true, sp.false) or isinstance(expression, (sp.logic.boolalg.BooleanFunction, sp.Contains)):
            kind = "logical"
        text = expression_input(expression) if kind in ("equation", "list") else None
        if node.kind == "call" and node.value == "Display":
            text = state.details["presentation"]["text"]
        result = EvaluationResult(kind, text or sp.sstr(expression), latex=sp.latex(expression),
                                input=candidate, conditions=tuple(dict.fromkeys(condition_text(restrictions) + tuple(state.conditions))),
                                warnings=tuple(dict.fromkeys(warnings)),
                                status="approximate" if not exact and state.status == "evaluated" else state.status,
                                exact=exact, details=state.details)
        return result, expression
    except MathechanError:
        raise
    except (ArithmeticError, TypeError, ValueError, RecursionError, NotImplementedError) as error:
        raise MathechanError(f"No se pudo evaluar la expresión: {error}") from error


def evaluate(source):
    """Evaluate one expression without session definitions or assignments."""
    return _evaluate_node(Parser(source).parse(), source)[0]
