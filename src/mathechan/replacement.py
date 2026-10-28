"""Bounded immediate and delayed rules with first-match tree replacement."""

from dataclasses import replace

import sympy as sp
from sympy.core.symbol import Str

from .semantic_types import HeldExpression


class RuleValue(sp.Basic):
    """Inert data: left side, right side, patterns, exclusions, requirements, delay."""

    def _sympystr(self, printer):
        left, right, _, _, _, delayed = self.args
        return f"{'RuleDelayed' if delayed is sp.true else 'Rule'}[{printer.doprint(left)},{printer.doprint(right)}]"

    def _latex(self, printer):
        return printer._print(self.args[0]) + r"\to " + printer._print(self.args[1])


def _pattern_nodes(node):
    result = {}
    pending = [node]
    while pending:
        child = pending.pop()
        if child.kind == "pattern":
            kind = child.children[0].value
            if child.value in result and result[child.value] != kind:
                raise ValueError("Un patrón no puede declarar tipos incompatibles.")
            result[child.value] = kind
        pending.extend(child.children)
    if len(result) > 8:
        raise ValueError("Una regla admite hasta ocho patrones escalares.")
    return result


def _rewrite_patterns(node):
    if node.kind == "pattern":
        return replace(node, kind="name", children=())
    return replace(node, children=tuple(_rewrite_patterns(child) for child in node.children))


def _valid_value(value):
    if isinstance(value, (sp.Tuple, sp.ImmutableMatrix)):
        return len(value) <= 64 and all(_valid_value(item) for item in value)
    return isinstance(value, sp.Basic) and not isinstance(value, (RuleValue, HeldExpression))


def replacement_call(node, build, restrictions, state, bindings, functions, definitions):
    from .language_ops import EvaluationState, arity, checked_restrictions
    from .domains import condition_text

    def read(child, target=None, child_state=None, scope=None, definition_scope=None):
        return build(child, restrictions if target is None else target,
                     state if child_state is None else child_state,
                     bindings if scope is None else scope, functions,
                     definitions if definition_scope is None else definition_scope)

    if node.value in ("Rule", "RuleDelayed"):
        arity(node, 2)
        patterns = _pattern_nodes(node.children[0])
        from .session import Session
        for pattern_name in patterns:
            Session._check_name(pattern_name)
        local_definitions = {name: value for name, value in definitions.items() if name not in patterns}
        scope = {**bindings, **{name: sp.Wild(name) for name in patterns}}
        child = EvaluationState(sum_terms=state.sum_terms, assumptions=state.assumptions,
                                call_depth=state.call_depth, steps=state.steps)
        child.assumptions = sp.And(*(condition for condition in sp.And.make_args(state.assumptions)
                                    if not {symbol.name for symbol in condition.free_symbols} & set(patterns)))
        local = []
        left = read(_rewrite_patterns(node.children[0]), local, child, scope, local_definitions)
        if not isinstance(left, sp.Basic) or isinstance(left, (HeldExpression, RuleValue)):
            raise ValueError("El lado izquierdo debe ser una expresión matemática admitida.")
        delayed = node.value == "RuleDelayed"
        if delayed:
            right = HeldExpression.from_node(node.children[1])
        else:
            scope = {**bindings, **{name: sp.Symbol(name) for name in patterns}}
            right = read(node.children[1], local, child, scope, local_definitions)
            if not _valid_value(right):
                raise ValueError("El lado derecho requiere un valor matemático escalar, lista o matriz.")
        if sp.count_ops(left) > 128 or len(local) > 64:
            raise ValueError("La regla excede el presupuesto estructural.")
        state.steps, state.sum_terms = child.steps, child.sum_terms
        state.approximate_inputs |= child.approximate_inputs
        state.warnings.extend(child.warnings)
        required = list(child.requirements)
        if child.assumptions is not sp.true:
            required.append(child.assumptions)
        return RuleValue(left, right, sp.Tuple(*(sp.Tuple(Str(name), Str(kind)) for name, kind in patterns.items())),
                         sp.Tuple(*local), sp.Tuple(*required), sp.true if delayed else sp.false)

    arity(node, 2)
    expression_state = EvaluationState(sum_terms=state.sum_terms, assumptions=state.assumptions,
                                       call_depth=state.call_depth, steps=state.steps)
    local = []
    expression = read(node.children[0], local, expression_state)
    if not _valid_value(expression):
        raise ValueError("ReplaceAll requiere una expresión, ecuación, lista o matriz.")
    state.steps, state.sum_terms = expression_state.steps, expression_state.sum_terms
    state.approximate_inputs |= expression_state.approximate_inputs
    state.extended_positive_infinity |= expression_state.extended_positive_infinity
    raw = read(node.children[1])
    rules = tuple(raw) if isinstance(raw, sp.Tuple) else (raw,)
    if len(rules) > 64 or any(not isinstance(rule, RuleValue) for rule in rules):
        raise ValueError("ReplaceAll requiere una regla o lista de hasta 64 reglas.")
    state.steps = max(state.steps, expression_state.steps)
    state.sum_terms = max(state.sum_terms, expression_state.sum_terms)
    new_restrictions, new_requirements = [], []

    def transform(value, depth=0):
        state.steps += 1
        if state.steps > 10000 or depth > 40:
            raise ValueError("ReplaceAll excede 10000 pasos o 40 niveles.")
        for rule in rules:
            left, right, patterns, excluded, required, delayed = rule.args
            matches = {} if value == left else None
            if matches is None and patterns and (isinstance(left, sp.Wild) or value.func == left.func):
                matches = value.match(left)
            if matches is None:
                continue
            accepted = True
            mapping = dict(matches)
            for name, kind in patterns:
                argument = matches.get(sp.Wild(str(name)))
                if (not isinstance(argument, sp.Expr) or argument.is_commutative is not True
                        or str(kind) == "Integer" and not isinstance(argument, sp.Integer)
                        or str(kind) == "Real" and not isinstance(argument, sp.Float)):
                    accepted = False
                    break
                mapping[sp.Symbol(str(name))] = argument
            if not accepted:
                continue
            new_restrictions.extend(item.xreplace(mapping) for item in excluded)
            new_requirements.extend(item.xreplace(mapping) for item in required)
            if delayed is sp.true:
                scope = {**bindings, **{str(name): mapping[sp.Symbol(str(name))] for name, _ in patterns}}
                return read(right.node, new_restrictions, state, scope,
                            {name: definition for name, definition in definitions.items()
                             if name not in {str(n) for n, _ in patterns}})
            return right.xreplace(mapping)
        if isinstance(value, sp.ImmutableMatrix):
            return value.applyfunc(lambda item: transform(item, depth + 1))
        if isinstance(value, sp.Piecewise):
            branches = []
            for expression, condition in value.args:
                condition = sp.simplify(transform(condition, depth + 1))
                if condition is sp.false:
                    continue
                branches.append((transform(expression, depth + 1), condition))
                if condition is sp.true:
                    break
            return sp.Piecewise(*branches)
        if not value.args:
            return value
        args = tuple(transform(item, depth + 1) for item in value.args)
        if args == value.args:
            return value
        if isinstance(value, sp.Equality):
            return sp.Eq(*args, evaluate=False)
        if value.func is sp.Pow and len(args) == 2:
            base, exponent = args
            if exponent.is_number and (exponent.is_real is not True or abs(exponent) > 1000):
                raise ValueError("La potencia sustituida excede el límite experimental ±1000.")
            if isinstance(base, sp.Rational) and isinstance(exponent, sp.Rational):
                bits = max(abs(int(base.p)).bit_length(), int(base.q).bit_length())
                if base not in (0, 1, -1) and bits*abs(int(exponent.p)) > 12000:
                    raise ValueError("La potencia sustituida excede 12000 bits estimados.")
        return value.func(*args)

    # Bound variables and retained operators need explicit scope-aware rules,
    # rather than rewriting their internal integration/series specifications.
    if expression.has(sp.Integral, sp.Sum, sp.Product, sp.Limit, sp.Order, sp.Derivative):
        raise ValueError("ReplaceAll no reescribe operadores ligados pendientes ni órdenes de serie; use parámetros antes de calcular.")
    result = transform(expression)
    transformed_restrictions = [transform(item) for item in local]
    restrictions.extend(checked_restrictions(transformed_restrictions + new_restrictions))
    for condition in (expression_state.assumptions, *expression_state.requirements):
        new_requirements.append(transform(condition))
    for condition in new_requirements:
        condition = sp.simplify(condition)
        if condition is sp.false:
            raise ValueError("La regla viola una condición original del cálculo.")
        if condition is not sp.true:
            state.requirements.append(condition)
            state.conditions.append(sp.sstr(condition))
            state.mark_status("conditional")
    state.warnings.extend(expression_state.warnings)
    if result.has(sp.Piecewise):
        state.mark_status("conditional")
    elif expression_state.status in ("unresolved", "unverified", "no_limit", "divergent", "series"):
        state.mark_status(expression_state.status)
    if expression_state.details:
        state.details["replacement_provenance"] = expression_state.details
    state.details["replacement"] = {"rules": len(rules), "strategy": "first match, one pass; inserted values not revisited"}
    return result
