"""Isolated immediate mathematical definitions and explicit session commands."""

from dataclasses import replace

import sympy as sp

from .definitions import StoredDefinition, UserFunction, DeferredDefinition, DeferredFunction
from .domains import condition_text
from .assumptions import ASSUMPTION_CALLS
from .kernel import FUNCTIONS, EvaluationResult, MathechanError, Parser, _evaluate_node
from .language_ops import SCIENTIFIC_CALLS
from .semantic_types import SEMANTIC_CALLS, HeldExpression, _source

MAX_DEFINITIONS = 64
SESSION_COMMANDS = frozenset({
    "Clear", "ClearAll", "Definition", "Define", "Assume", "Assumptions", "ClearAssumptions",
    "SetDelayed", "DefineDelayed", "DefinePattern",
})
PROTECTED_NAMES = frozenset(FUNCTIONS) | SCIENTIFIC_CALLS | SESSION_COMMANDS | ASSUMPTION_CALLS | SEMANTIC_CALLS | {
    "Pi", "E", "Imag", "Infinity", "Plot", "Reals", "Complexes", "Integers", "True", "False",
    "If", "IntegerPattern", "RealPattern", "ScalarPattern",
}
ASSIGNABLE_STATUSES = frozenset({"evaluated", "approximate", "verified", "solved", "series"})


class Session:
    """Keep at most 64 definitions, with explicit deferred evaluation when requested."""

    def __init__(self):
        self._definitions = {}
        self._assumptions = sp.S.true

    def evaluate(self, source):
        """Evaluate an expression or run one independent session command."""
        node = Parser(source, allow_assignment=True).parse()
        if node.kind == "call" and node.value in SESSION_COMMANDS:
            return self._command(node, source)
        self._reject_nested_commands(node)
        name = node.value if node.kind == "assignment" else None
        if name is not None:
            self._check_name(name)
            self._check_capacity(name)
            node = node.children[0]
        capture = {}
        result, value = _evaluate_node(node, source, dict(self._definitions),
                                       assumptions=self._assumptions, capture=capture)
        if name is not None:
            stored = self._snapshot(value, result, capture)
            if any(sp.Symbol(name) in item.free_symbols for item in
                   (stored.value, *stored.restrictions)):
                raise MathechanError("Una definición inmediata no puede depender de sí misma.")
            self._check_assumptions({**self._definitions, name: stored})
            result = replace(result, details={**result.details, "assignment": {"name": name}})
            self._definitions[name] = stored
        elif (result.input is not None and value is not None
              and any(symbol.name in self._definitions for symbol in value.free_symbols)):
            warning = ("La entrada reutilizable se verifica sin definiciones de sesión; "
                       "volver a evaluarla aquí puede sustituir nombres definidos.")
            result = replace(result, warnings=tuple(dict.fromkeys((*result.warnings, warning))))
        return result

    @staticmethod
    def _reject_nested_commands(node):
        pending = [node]
        while pending:
            child = pending.pop()
            if child.kind == "call" and child.value in SESSION_COMMANDS:
                raise MathechanError(f"{child.value} solo se admite como comando de sesión independiente.")
            pending.extend(child.children)

    @staticmethod
    def _snapshot(value, result, capture):
        if result.details.get("local_identity_only"):
            raise MathechanError("La identidad sólo es local y no tiene un entorno de validez guardable; no se almacena como función global.")
        conditional = (result.status == "conditional" and
                       (capture.get("restrictions") or capture.get("requirements")))
        def supported(item):
            from sympy.assumptions.assume import AppliedPredicate
            from sympy.logic.boolalg import BooleanFunction
            from .replacement import RuleValue
            from .finite_probability import FiniteDistribution
            from .joint_probability import JointFiniteDistribution
            if isinstance(item, (FiniteDistribution, JointFiniteDistribution)):
                return all(supported(child) for child in item.args)
            if (item is sp.true or item is sp.false or
                    isinstance(item, (BooleanFunction, AppliedPredicate, sp.Contains))):
                return not item.has(sp.zoo, sp.nan, sp.oo, -sp.oo)
            if isinstance(item, RuleValue):
                return True
            if isinstance(item, HeldExpression):
                return True
            if isinstance(item, (sp.Tuple, sp.ImmutableMatrix)):
                return len(item) <= 64 and all(supported(child) for child in item)
            if isinstance(item, sp.Expr) and item.has(sp.Order):
                core = item.removeO()
                return (core.is_finite is not False and not core.has(sp.zoo, sp.nan, sp.oo, -sp.oo)
                        and all(not order.expr.has(sp.zoo, sp.nan, sp.oo, -sp.oo)
                                for order in item.atoms(sp.Order)))
            return (isinstance(item, sp.Expr) and item.is_commutative is True
                    and item.is_finite is not False and not item.has(sp.zoo, sp.nan, sp.oo, -sp.oo))

        if (not supported(value)
                or (result.status not in ASSIGNABLE_STATUSES and not conditional)):
            raise MathechanError("La asignación requiere escalares finitos, listas, matrices "
                                 "o expresiones Hold sin resultados pendientes de verificar.")
        return StoredDefinition(value, tuple(capture.get("restrictions", ())),
                                tuple(capture.get("requirements", ())), tuple(result.warnings))

    @staticmethod
    def _check_name(name):
        if name in PROTECTED_NAMES:
            raise MathechanError(f"El nombre {name} está protegido y no admite redefinición.")

    def _check_capacity(self, name):
        if name not in self._definitions and len(self._definitions) >= MAX_DEFINITIONS:
            raise MathechanError("La sesión admite como máximo 64 definiciones.")

    @staticmethod
    def _command_name(node):
        if len(node.children) != 1 or node.children[0].kind != "name":
            raise MathechanError(f"{node.value} requiere un único nombre de variable: {node.value}[x].")
        name = node.children[0].value
        Session._check_name(name)
        return name

    def _command(self, node, source):
        operation = node.value
        if operation in ("Define", "DefineDelayed", "DefinePattern"):
            return self._define(node, source, delayed=operation != "Define",
                                patterned=operation == "DefinePattern")
        if operation == "SetDelayed":
            if len(node.children) != 2 or node.children[0].kind != "name":
                raise MathechanError("Use SetDelayed[nombre,expresión].")
            name, body = node.children[0].value, node.children[1]
            self._check_name(name)
            self._check_capacity(name)
            self._reject_nested_commands(body)
            self._definitions[name] = DeferredDefinition(body)
            return self._definition(name)
        if operation in ("ClearAll", "Assumptions", "ClearAssumptions"):
            if node.children:
                raise MathechanError(f"{operation} no admite argumentos.")
            if operation == "ClearAll":
                count = len(self._definitions)
                self._definitions.clear()
                return EvaluationResult("session", "Definiciones eliminadas.",
                                        details={"clear_all": {"removed": count}})
            if operation == "ClearAssumptions":
                self._assumptions = sp.S.true
            return EvaluationResult("session", sp.sstr(self._assumptions),
                                    details={"assumptions": sp.sstr(self._assumptions)})
        if operation == "Assume":
            return self._assume(node, source)
        name = self._command_name(node)
        if operation == "Clear":
            removed = name in self._definitions
            result = EvaluationResult("session", f"Definición eliminada: {name}." if removed else f"Sin definición: {name}.",
                                      details={"clear": {"name": name, "removed": removed}})
            self._definitions.pop(name, None)
            return result
        return self._definition(name)

    def _definition(self, name):
        defined = name in self._definitions
        definition = {"name": name, "defined": defined}
        text, exact = f"Sin definición: {name}.", True
        conditions = ()
        display_name = name
        if defined:
            stored = self._definitions[name]
            if isinstance(stored, (DeferredDefinition, DeferredFunction)):
                node = stored.node
                if isinstance(stored, DeferredFunction):
                    reverse = dict(zip(stored.parameters, stored.names))

                    def public_names(child):
                        return replace(child, value=reverse.get(child.value, child.value)
                                       if child.kind == "name" else child.value,
                                       children=tuple(public_names(item) for item in child.children))

                    node = public_names(node)
                    definition["parameters"] = list(stored.names)
                    if stored.patterns:
                        definition["patterns"] = list(stored.patterns)
                    display_name = f"{name}[{','.join(stored.names)}]"
                definition.update(value=_source(node), delayed=True)
                return EvaluationResult("session", f"{display_name} := {definition['value']}",
                                        details={"definition": definition})
            function = isinstance(stored, UserFunction)
            body = stored.body if function else stored
            value = body.value
            substitutions = {}
            if function:
                free_names = {
                    symbol.name for expression in (body.value, *body.restrictions, *body.requirements)
                    for symbol in expression.free_symbols if symbol not in stored.parameters
                }
                labels = []
                for index, parameter in enumerate(stored.names):
                    label = parameter
                    suffix = index + 1
                    while label in free_names or label in labels:
                        label = f"arg{suffix}"
                        suffix += 1
                    labels.append(label)
                substitutions = dict(zip(stored.parameters, map(sp.Symbol, labels)))
                value = value.xreplace(substitutions)
                definition["parameters"] = list(stored.names)
                if tuple(labels) != stored.names:
                    definition["parameter_labels"] = labels
                display_name = f"{name}[{','.join(labels)}]"
            conditions = tuple(dict.fromkeys((
                *condition_text(tuple(item.xreplace(substitutions) for item in body.restrictions)),
                *(sp.sstr(item.xreplace(substitutions)) for item in body.requirements
                  if item is not sp.true),
            )))
            exact = not value.has(sp.Float)
            definition.update(value=sp.sstr(value), exact=exact)
            text = f"{display_name} = {definition['value']}"
        return EvaluationResult("session", text, exact=exact, conditions=conditions,
                                details={"definition": definition})

    def _define(self, node, source, delayed=False, patterned=False):
        if len(node.children) != 3 or node.children[0].kind != "name":
            raise MathechanError("Use Define[f,{x,y},expresión].")
        name = node.children[0].value
        self._check_name(name)
        self._check_capacity(name)
        parameters = node.children[1]
        patterns = ()
        if patterned:
            if (parameters.kind != "list" or not parameters.children
                    or any(child.kind != "call" or child.value not in
                           ("IntegerPattern", "RealPattern", "ScalarPattern")
                           or len(child.children) != 1 or child.children[0].kind != "name"
                           for child in parameters.children)):
                raise MathechanError("DefinePattern admite IntegerPattern, RealPattern o ScalarPattern de un nombre.")
            patterns = tuple(child.value for child in parameters.children)
            parameters = replace(parameters, children=tuple(child.children[0] for child in parameters.children))
        if (parameters.kind != "list" or not 1 <= len(parameters.children) <= 8
                or any(child.kind != "name" for child in parameters.children)):
            raise MathechanError("Define requiere una lista de 1 a 8 parámetros simbólicos.")
        names = tuple(child.value for child in parameters.children)
        if len(set(names)) != len(names) or name in names:
            raise MathechanError("Los parámetros deben ser distintos y diferentes del nombre de función.")
        for parameter in names:
            self._check_name(parameter)
        body_node = node.children[2]
        self._reject_nested_commands(body_node)
        pending = [body_node]
        while pending:
            child = pending.pop()
            if not delayed and child.value == name and child.kind in ("name", "call"):
                raise MathechanError("No se admiten definiciones funcionales recursivas.")
            pending.extend(child.children)
        dummies = tuple(sp.Dummy(parameter) for parameter in names)
        # Rename only occurrences written in the function's own syntax tree.
        # A global snapshot may introduce another free symbol with the same
        # printed name; that symbol must not become a function parameter.
        aliases = tuple(f"__parameter{index}" for index in range(len(names)))
        renaming = dict(zip(names, aliases))

        def rename_parameters(child):
            return replace(
                child,
                value=renaming.get(child.value, child.value) if child.kind == "name" else child.value,
                children=tuple(rename_parameters(item) for item in child.children),
            )

        body_node = rename_parameters(body_node)
        if delayed:
            self._definitions[name] = DeferredFunction(aliases, names, body_node, patterns)
            return self._definition(name)
        scope = {key: value for key, value in self._definitions.items() if key != name}
        scope.update(zip(aliases, dummies))
        capture = {}
        local_assumptions = sp.And(*(item for item in sp.And.make_args(self._assumptions)
                                    if not {symbol.name for symbol in item.free_symbols} & set(names)))
        result, value = _evaluate_node(body_node, source, scope,
                                       assumptions=local_assumptions, capture=capture)
        body = self._snapshot(value, result, capture)
        formals = dict(zip(map(sp.Symbol, aliases), dummies))
        body = replace(body, value=body.value.xreplace(formals),
                       restrictions=tuple(item.xreplace(formals) for item in body.restrictions),
                       requirements=tuple(item.xreplace(formals) for item in body.requirements))
        function = UserFunction(dummies, body, names)
        self._definitions[name] = function
        return self._definition(name)

    def _assume(self, node, source):
        from .assumptions import combine_assumptions

        if len(node.children) != 1:
            raise MathechanError("Assume requiere una condición matemática.")
        self._reject_nested_commands(node.children[0])
        capture = {}
        _, condition = _evaluate_node(node.children[0], source, capture=capture)
        try:
            condition = sp.And(
                condition, *(sp.Ne(item, 0) for item in capture.get("restrictions", ())),
                *capture.get("requirements", ()),
            )
            combined = combine_assumptions(self._assumptions, condition)
        except (ValueError, TypeError, ArithmeticError) as error:
            raise MathechanError(str(error)) from error
        self._check_assumptions(self._definitions, combined)
        self._assumptions = combined
        return EvaluationResult("session", sp.sstr(combined), details={"assumptions": sp.sstr(combined)})

    def _check_assumptions(self, definitions, assumptions=None):
        from .assumptions import validate_assumptions

        condition = self._assumptions if assumptions is None else assumptions
        mapping = {sp.Symbol(name): definition.value for name, definition in definitions.items()
                   if isinstance(definition, StoredDefinition) and isinstance(definition.value, sp.Expr)
                   and definition.value.is_number is True}
        try:
            validate_assumptions(condition.subs(mapping, simultaneous=True))
        except (ValueError, TypeError, ArithmeticError) as error:
            raise MathechanError(str(error)) from error

    def save(self, path):
        """Explicitly save typed session data without executing any stored syntax."""
        from .session_storage import save_session

        save_session(self, path)

    @classmethod
    def load(cls, path):
        """Read a validated session into a fresh object; never evaluate stored syntax."""
        from .session_storage import load_session

        return load_session(path, cls)
