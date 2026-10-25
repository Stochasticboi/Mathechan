"""Versioned, bounded session data; no executable source or Python objects on load."""

import json
import os
from pathlib import Path
import re
import tempfile

import sympy as sp
from sympy.assumptions.assume import AppliedPredicate
from sympy.core.relational import Relational
from sympy.functions.elementary.piecewise import ExprCondPair
from sympy.logic.boolalg import BooleanFunction

from .definitions import StoredDefinition, UserFunction, DeferredDefinition, DeferredFunction
from .semantic_types import HeldExpression
from .hyperbolic import HYPERBOLIC_FUNCTIONS

MAX_BYTES = 2 * 1024 * 1024
MAX_NODES = 20000
NAME = re.compile(r"[A-Za-z][A-Za-z0-9]*\Z")
CONSTRUCTORS = {
    **{function.__name__: function for function in HYPERBOLIC_FUNCTIONS.values()},
    "Add": sp.Add, "Mul": sp.Mul, "Pow": sp.Pow,
    "sin": sp.sin, "cos": sp.cos, "exp": sp.exp, "log": sp.log,
    "Abs": sp.Abs, "asin": sp.asin, "acos": sp.acos, "atan": sp.atan,
    "gamma": sp.gamma, "Tuple": sp.Tuple,
    "conjugate": sp.conjugate, "re": sp.re, "im": sp.im,
    "Equality": sp.Eq, "Unequality": sp.Ne, "StrictGreaterThan": sp.Gt,
    "GreaterThan": sp.Ge, "StrictLessThan": sp.Lt, "LessThan": sp.Le,
    "And": sp.And, "Or": sp.Or, "Not": sp.Not, "Contains": sp.Contains,
    "Interval": sp.Interval, "Union": sp.Union, "Intersection": sp.Intersection,
    "Complement": sp.Complement, "FiniteSet": sp.FiniteSet,
    "ExprCondPair": ExprCondPair, "Piecewise": sp.Piecewise,
    "Order": sp.Order,
}
CONSTANTS = {"Pi": sp.pi, "E": sp.E, "I": sp.I, "Infinity": sp.oo,
             "NegativeInfinity": -sp.oo, "True": sp.true, "False": sp.false,
             "Reals": sp.S.Reals, "Complexes": sp.S.Complexes,
             "Integers": sp.S.Integers, "Naturals": sp.S.Naturals,
             "Naturals0": sp.S.Naturals0, "EmptySet": sp.S.EmptySet}


def _keys(data, expected):
    if not isinstance(data, dict) or set(data) != set(expected):
        raise ValueError("Campos de sesión desconocidos o incompletos.")


def _integer(value, minimum=None, maximum=None):
    if type(value) is not int or (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        raise ValueError("Entero de sesión fuera de límites.")
    return value


def _name(value, internal=False):
    if not isinstance(value, str) or len(value) > 4096 or not (
            NAME.fullmatch(value) or internal and re.fullmatch(r"__parameter[0-7]", value)):
        raise ValueError("Nombre de sesión no admitido.")
    return value


class Codec:
    def __init__(self):
        self.nodes = 0
        self.dummies = {}
        self.dummy_ids = {}

    def tick(self, depth):
        self.nodes += 1
        if depth > 64 or self.nodes > MAX_NODES:
            raise ValueError("La sesión excede el límite de estructura.")

    def ast_encode(self, node, depth=0):
        self.tick(depth)
        return {"kind": node.kind, "value": node.value,
                "children": [self.ast_encode(child, depth + 1) for child in node.children]}

    def ast_decode(self, data, depth=0):
        from .kernel import Node

        self.tick(depth)
        if depth > 40:
            raise ValueError("AST de sesión demasiado profundo.")
        _keys(data, ("kind", "value", "children"))
        kind, value, children = data["kind"], data["value"], data["children"]
        if not isinstance(children, list) or len(children) > 256 or not isinstance(value, str):
            raise ValueError("AST de sesión inválido.")
        if kind == "name":
            _name(value, internal=True)
            if children:
                raise ValueError("Un nombre no admite hijos.")
        elif kind == "string":
            if value not in ("Cartesian", "Cylindrical", "Spherical", "Components", "Orthonormal") or children:
                raise ValueError("El texto no es una opción de coordenadas admitida.")
        elif kind == "number":
            if len(value) > 100 or not re.fullmatch(r"\d+(?:\.\d+)?", value) or children:
                raise ValueError("Número de AST inválido.")
        elif kind == "call":
            _name(value)
        elif kind == "pattern":
            _name(value)
            if (len(children) != 1 or children[0].get("kind") != "name"
                    or children[0].get("value") not in ("Scalar", "Integer", "Real")):
                raise ValueError("Patrón de regla inválido.")
        elif kind == "list":
            if value != "" or len(children) > 64:
                raise ValueError("Lista de AST inválida.")
        elif kind == "unary":
            if value not in ("+", "-") or len(children) != 1:
                raise ValueError("Operador unario inválido.")
        elif kind == "binary":
            if value not in ("+", "-", "*", "/", "^", "==", "!=", "<", "<=", ">", ">=") or len(children) != 2:
                raise ValueError("Operador binario inválido.")
        else:
            raise ValueError("Tipo de AST no admitido.")
        return Node(kind, value, tuple(self.ast_decode(child, depth + 1) for child in children))

    def encode(self, value, depth=0):
        self.tick(depth)
        from .finite_probability import FiniteDistribution
        from .joint_probability import JointFiniteDistribution
        if isinstance(value, JointFiniteDistribution):
            return {"type": "joint_finite_distribution", "states": self.encode(value.states, depth + 1),
                    "probabilities": self.encode(value.probabilities, depth + 1)}
        if isinstance(value, FiniteDistribution):
            return {"type": "finite_distribution", "states": self.encode(value.states, depth + 1),
                    "probabilities": self.encode(value.probabilities, depth + 1)}
        from .replacement import RuleValue
        if isinstance(value, RuleValue):
            left, right, patterns, excluded, required, delayed = value.args
            return {"type": "rule", "left": self.encode(left, depth + 1),
                    "right": self.encode(right, depth + 1),
                    "patterns": [[str(name), str(kind)] for name, kind in patterns],
                    "excluded": [self.encode(item, depth + 1) for item in excluded],
                    "required": [self.encode(item, depth + 1) for item in required],
                    "delayed": delayed is sp.true}
        if isinstance(value, sp.Wild):
            return {"type": "wild", "name": value.name}
        if isinstance(value, HeldExpression):
            return {"type": "held", "node": self.ast_encode(value.node, depth + 1)}
        for name, constant in CONSTANTS.items():
            if value is constant:
                return {"type": "constant", "name": name}
        if isinstance(value, sp.Dummy):
            identifier = self.dummy_ids.setdefault(value, len(self.dummy_ids))
            return {"type": "dummy", "id": identifier, "name": value.name}
        if isinstance(value, sp.Symbol):
            if value != sp.Symbol(value.name):
                raise ValueError("Los símbolos con propiedades internas no se serializan implícitamente.")
            return {"type": "symbol", "name": value.name}
        if isinstance(value, sp.Integer):
            return {"type": "integer", "value": str(value)}
        if isinstance(value, sp.Rational):
            return {"type": "rational", "p": str(value.p), "q": str(value.q)}
        if isinstance(value, sp.Float):
            sign, mantissa, exponent, bits = value._mpf_
            return {"type": "float", "mpf": [sign, str(mantissa), exponent, bits], "precision": value._prec}
        if isinstance(value, sp.ImmutableMatrix):
            return {"type": "matrix", "rows": value.rows, "cols": value.cols,
                    "items": [self.encode(item, depth + 1) for item in value]}
        name = value.func.__name__ if isinstance(value, sp.Basic) else None
        if name not in CONSTRUCTORS:
            raise ValueError("El tipo matemático no está admitido en archivos de sesión.")
        return {"type": "expression", "constructor": name,
                "args": [self.encode(item, depth + 1) for item in value.args]}

    @staticmethod
    def decimal(value, positive=False):
        if not isinstance(value, str) or len(value) > 4096 or not re.fullmatch(r"-?\d+", value):
            raise ValueError("Entero decimal inválido en sesión.")
        number = int(value)
        if positive and number <= 0:
            raise ValueError("Se requiere un entero positivo.")
        return number

    def decode(self, data, depth=0):
        self.tick(depth)
        if not isinstance(data, dict) or "type" not in data:
            raise ValueError("Dato matemático de sesión inválido.")
        kind = data["type"]
        if kind == "joint_finite_distribution":
            from .joint_probability import JointFiniteDistribution
            _keys(data, ("type", "states", "probabilities"))
            states = self.decode(data["states"], depth + 1)
            probabilities = self.decode(data["probabilities"], depth + 1)
            return JointFiniteDistribution(states, probabilities)
        if kind == "finite_distribution":
            from .finite_probability import FiniteDistribution
            _keys(data, ("type", "states", "probabilities"))
            states = self.decode(data["states"], depth + 1)
            probabilities = self.decode(data["probabilities"], depth + 1)
            return FiniteDistribution(states, probabilities)
        if kind == "wild":
            _keys(data, ("type", "name"))
            return sp.Wild(_name(data["name"]))
        if kind == "rule":
            from .replacement import RuleValue
            from sympy.core.symbol import Str
            _keys(data, ("type", "left", "right", "patterns", "excluded", "required", "delayed"))
            raw = data["patterns"]
            if not isinstance(raw, list) or len(raw) > 8 or type(data["delayed"]) is not bool:
                raise ValueError("Regla serializada inválida.")
            patterns = []
            for pair in raw:
                if (not isinstance(pair, list) or len(pair) != 2
                        or pair[1] not in ("Integer", "Real", "Scalar")):
                    raise ValueError("Tipo de patrón inválido.")
                from .session import Session
                Session._check_name(_name(pair[0]))
                patterns.append(sp.Tuple(Str(_name(pair[0])), Str(pair[1])))
            if len({str(pair[0]) for pair in patterns}) != len(patterns):
                raise ValueError("Patrones duplicados.")
            if any(not isinstance(data[key], list) or len(data[key]) > 64 for key in ("excluded", "required")):
                raise ValueError("Condiciones de regla inválidas.")
            left, right = (self.decode(data[key], depth + 1) for key in ("left", "right"))
            excluded = sp.Tuple(*(self.decode(item, depth + 1) for item in data["excluded"]))
            required = sp.Tuple(*(self.decode(item, depth + 1) for item in data["required"]))
            if (not isinstance(left, sp.Basic) or isinstance(left, (RuleValue, HeldExpression))
                    or data["delayed"] and not isinstance(right, HeldExpression)
                    or not data["delayed"] and isinstance(right, (RuleValue, HeldExpression))
                    or left.atoms(sp.Wild) != {sp.Wild(str(pair[0])) for pair in patterns}
                    or any(not isinstance(item, sp.Expr) for item in excluded)
                    or any(not (item in (sp.true, sp.false) or isinstance(item, (Relational, BooleanFunction, AppliedPredicate, sp.Contains)))
                           for item in required)):
                raise ValueError("Estructura de regla inválida.")
            return RuleValue(left, right, sp.Tuple(*patterns), excluded, required,
                             sp.true if data["delayed"] else sp.false)
        if kind == "constant":
            _keys(data, ("type", "name"))
            if data["name"] not in CONSTANTS:
                raise ValueError("Constante desconocida.")
            return CONSTANTS[data["name"]]
        if kind in ("symbol", "dummy"):
            _keys(data, ("type", "name", "id") if kind == "dummy" else ("type", "name"))
            name = _name(data["name"])
            if kind == "symbol":
                if name in ("Pi", "E", "Imag", "Infinity", "True", "False", "Reals", "Complexes", "Integers"):
                    raise ValueError("Un símbolo ordinario no puede ocultar una constante del lenguaje.")
                return sp.Symbol(name)
            identifier = _integer(data["id"], 0, 1024)
            if identifier in self.dummies and self.dummies[identifier].name != name:
                raise ValueError("Identificador de parámetro inconsistente.")
            return self.dummies.setdefault(identifier, sp.Dummy(name))
        if kind == "integer":
            _keys(data, ("type", "value"))
            return sp.Integer(self.decimal(data["value"]))
        if kind == "rational":
            _keys(data, ("type", "p", "q"))
            return sp.Rational(self.decimal(data["p"]), self.decimal(data["q"], positive=True))
        if kind == "float":
            _keys(data, ("type", "mpf", "precision"))
            mpf = data["mpf"]
            if not isinstance(mpf, list) or len(mpf) != 4:
                raise ValueError("Representación Float inválida.")
            sign = _integer(mpf[0], 0, 1)
            mantissa = self.decimal(mpf[1])
            exponent = _integer(mpf[2], -1000000, 1000000)
            bits = _integer(mpf[3], 0, 20000)
            precision = _integer(data["precision"], 1, 20000)
            if mantissa < 0 or mantissa.bit_length() != bits or mantissa and not mantissa & 1:
                raise ValueError("Mantisa Float no canónica.")
            if bits > precision:
                raise ValueError("La mantisa Float excede la precisión declarada.")
            if not mantissa and (sign or exponent or bits):
                raise ValueError("El cero Float debe ser canónico.")
            return sp.Float((sign, mantissa, exponent, bits), precision=precision)
        if kind == "held":
            _keys(data, ("type", "node"))
            return HeldExpression.from_node(self.ast_decode(data["node"], depth + 1))
        if kind == "matrix":
            _keys(data, ("type", "rows", "cols", "items"))
            rows, cols = _integer(data["rows"], 1, 64), _integer(data["cols"], 1, 64)
            if rows * cols > 64 or not isinstance(data["items"], list) or len(data["items"]) != rows * cols:
                raise ValueError("Dimensiones de matriz inválidas.")
            items = [self.decode(item, depth + 1) for item in data["items"]]
            if any(not isinstance(item, sp.Expr) or item.is_commutative is not True for item in items):
                raise ValueError("La matriz requiere escalares.")
            return sp.ImmutableMatrix(rows, cols, items)
        if kind != "expression":
            raise ValueError("Tipo de dato matemático no admitido.")
        _keys(data, ("type", "constructor", "args"))
        name, raw = data["constructor"], data["args"]
        if name not in CONSTRUCTORS or not isinstance(raw, list) or len(raw) > 256:
            raise ValueError("Constructor matemático no admitido.")
        args = [self.decode(item, depth + 1) for item in raw]
        if name == "ExprCondPair":
            if (len(args) != 2 or not isinstance(args[0], sp.Expr) or not (
                    args[1] in (sp.true, sp.false) or
                    isinstance(args[1], (Relational, BooleanFunction, AppliedPredicate, sp.Contains)))):
                raise ValueError("Par expresión-condición inválido.")
            return ExprCondPair(*args)
        if name == "Order":
            if (not 2 <= len(args) <= 9 or not isinstance(args[0], sp.Expr)
                    or args[0].has(sp.oo, -sp.oo, sp.zoo, sp.nan)
                    or any(not isinstance(item, sp.Tuple) or len(item) != 2
                           or not isinstance(item[0], sp.Symbol) or not isinstance(item[1], sp.Expr)
                           or item[1].is_extended_real is not True
                           or item[1].has(item[0]) for item in args[1:])):
                raise ValueError("Orden de serie serializado inválido.")
            return sp.Order(*args)
        if name == "Piecewise":
            if not 1 <= len(args) <= 64 or any(not isinstance(item, ExprCondPair) for item in args):
                raise ValueError("Piecewise requiere entre 1 y 64 pares expresión-condición.")
            return sp.Piecewise(*args, evaluate=False)
        if name == "Pow" and (len(args) != 2 or isinstance(args[1], sp.Expr)
                              and args[1].is_number and
                              (args[1].is_real is not True or abs(args[1]) > 1000)):
            raise ValueError("Potencia serializada fuera de límites.")
        if name == "Interval":
            if len(args) != 4:
                raise ValueError("Intervalo serializado inválido.")
            return sp.Interval(*args)
        if name in ("Tuple", "Union", "Intersection", "Complement", "FiniteSet"):
            return CONSTRUCTORS[name](*args)
        if name in ("Add", "Mul") and any(item.has(sp.Order) for item in args):
            return CONSTRUCTORS[name](*args)
        return CONSTRUCTORS[name](*args, evaluate=False)

    def definition_encode(self, value):
        if isinstance(value, StoredDefinition):
            return {"kind": "stored", "value": self.encode(value.value),
                    "restrictions": [self.encode(item) for item in value.restrictions],
                    "requirements": [self.encode(item) for item in value.requirements],
                    "warnings": list(value.warnings)}
        if isinstance(value, UserFunction):
            return {"kind": "function", "parameters": [self.encode(item) for item in value.parameters],
                    "names": list(value.names), "body": self.definition_encode(value.body)}
        if isinstance(value, DeferredDefinition):
            return {"kind": "deferred", "node": self.ast_encode(value.node)}
        if isinstance(value, DeferredFunction):
            return {"kind": "deferred_function", "parameters": list(value.parameters),
                    "names": list(value.names), "patterns": list(value.patterns), "node": self.ast_encode(value.node)}
        raise ValueError("Definición de sesión no admitida.")

    def definition_decode(self, data):
        from .session import Session

        if not isinstance(data, dict) or "kind" not in data:
            raise ValueError("Definición serializada inválida.")
        kind = data["kind"]
        if kind == "stored":
            _keys(data, ("kind", "value", "restrictions", "requirements", "warnings"))
            for name in ("restrictions", "requirements", "warnings"):
                if not isinstance(data[name], list) or len(data[name]) > 256:
                    raise ValueError("Metadatos de definición inválidos.")
            if any(not isinstance(item, str) or len(item) > 4096 for item in data["warnings"]):
                raise ValueError("Avisos de definición inválidos.")
            value = self.decode(data["value"])
            restrictions = tuple(self.decode(item) for item in data["restrictions"])
            requirements = tuple(self.decode(item) for item in data["requirements"])
            if any(not isinstance(item, sp.Expr) or item.is_zero is True
                   or item.has(sp.zoo, sp.nan, sp.oo, -sp.oo) for item in restrictions):
                raise ValueError("Las restricciones requieren expresiones escalares.")
            from .assumptions import validate_assumptions
            for item in requirements:
                validate_assumptions(item)
            validate_assumptions(sp.And(*requirements))
            from .kernel import EvaluationResult
            capture = {"restrictions": restrictions, "requirements": requirements}
            snapshot = Session._snapshot(value, EvaluationResult("expression", "", status="conditional"
                                        if restrictions or requirements else "evaluated"), capture)
            return StoredDefinition(snapshot.value, restrictions, requirements, tuple(data["warnings"]))
        if kind == "deferred":
            _keys(data, ("kind", "node"))
            node = self.ast_decode(data["node"])
            Session._reject_nested_commands(node)
            return DeferredDefinition(node)
        if kind not in ("function", "deferred_function"):
            raise ValueError("Tipo de definición desconocido.")
        _keys(data, ("kind", "parameters", "names", "body") if kind == "function" else
              ("kind", "parameters", "names", "patterns", "node"))
        names, parameters = data["names"], data["parameters"]
        if (not isinstance(names, list) or not 1 <= len(names) <= 8 or not isinstance(parameters, list)
                or len(parameters) != len(names) or len(set(map(str, names))) != len(names)):
            raise ValueError("Parámetros de función inválidos.")
        names = tuple(_name(item) for item in names)
        for name in names:
            Session._check_name(name)
        if kind == "function":
            parameters = tuple(self.decode(item) for item in parameters)
            if any(not isinstance(item, sp.Dummy) for item in parameters) or len(set(parameters)) != len(parameters):
                raise ValueError("Parámetros internos inválidos.")
            body = self.definition_decode(data["body"])
            if not isinstance(body, StoredDefinition):
                raise ValueError("El cuerpo inmediato requiere un snapshot.")
            return UserFunction(parameters, body, names)
        parameters = tuple(_name(item, internal=True) for item in parameters)
        if parameters != tuple(f"__parameter{index}" for index in range(len(names))):
            raise ValueError("Aliases de función diferida inválidos.")
        patterns = data["patterns"]
        if (not isinstance(patterns, list) or len(patterns) not in (0, len(names)) or
                any(item not in ("IntegerPattern", "RealPattern", "ScalarPattern") for item in patterns)):
            raise ValueError("Patrones de función no admitidos.")
        node = self.ast_decode(data["node"])
        Session._reject_nested_commands(node)
        return DeferredFunction(parameters, names, node, tuple(patterns))


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("Claves JSON duplicadas en sesión.")
        result[key] = value
    return result


def save_session(session, path):
    from .kernel import MathechanError

    temporary = None
    try:
        codec = Codec()
        document = {"format": "mathechan-session", "version": "0.1",
                    "definitions": {name: codec.definition_encode(value) for name, value in session._definitions.items()},
                    "assumptions": codec.encode(session._assumptions)}
        encoded = json.dumps(document, ensure_ascii=True, allow_nan=False).encode("utf-8")
        if len(encoded) > MAX_BYTES:
            raise ValueError("La sesión excede 2 MB.")
        # Validate the exact document before replacing an existing destination.
        _load_document(json.loads(encoded, object_pairs_hook=_pairs), type(session))
        destination = Path(path)
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".mathechan-session-", delete=False) as stream:
            temporary = stream.name
            stream.write(encoded)
        os.replace(temporary, destination)
        temporary = None
    except (OSError, ValueError, TypeError, ArithmeticError, RecursionError) as error:
        raise MathechanError(f"No se pudo guardar la sesión: {error}") from error
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def _load_document(document, cls):
    _keys(document, ("format", "version", "definitions", "assumptions"))
    if document["format"] != "mathechan-session" or document["version"] != "0.1":
        raise ValueError("Formato o versión de sesión no admitidos.")
    definitions = document["definitions"]
    if not isinstance(definitions, dict) or len(definitions) > 64:
        raise ValueError("La sesión admite como máximo 64 definiciones.")
    session, codec = cls(), Codec()
    decoded = {}
    for name, value in definitions.items():
        _name(name)
        session._check_name(name)
        decoded[name] = codec.definition_decode(value)
    assumptions = codec.decode(document["assumptions"])
    session._check_assumptions(decoded, assumptions)
    session._definitions, session._assumptions = decoded, assumptions
    return session


def load_session(path, cls):
    from .kernel import MathechanError

    try:
        with Path(path).open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("La sesión excede 2 MB.")
        document = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                              parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Constante JSON no admitida.")))
        return _load_document(document, cls)
    except (OSError, ValueError, TypeError, ArithmeticError, RecursionError, AttributeError) as error:
        raise MathechanError(f"No se pudo cargar la sesión: {error}") from error
