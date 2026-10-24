"""Local mathematical assumptions and conservative refinement, without global state."""

import sympy as sp
from sympy.assumptions.assume import AppliedPredicate
from sympy.core.relational import Relational
from sympy.logic.boolalg import BooleanFunction
from sympy.polys.polyerrors import BasePolynomialError

ASSUMPTION_CALLS = frozenset({'And', 'Or', 'Not', 'Element', 'Interval', 'Assuming', 'Refine', 'With'})


def predicates(condition):
    """Translate supported domain and sign statements to SymPy predicates."""
    if condition in (sp.true, sp.false):
        return condition
    if isinstance(condition, sp.Contains):
        value, domain = condition.args
        query = {sp.S.Reals: sp.Q.real, sp.S.Complexes: sp.Q.complex, sp.S.Integers: sp.Q.integer}.get(domain)
        if query is None and isinstance(domain, sp.Interval):
            return predicates(domain.as_relational(value))
        return query(value) if query is not None else condition
    if isinstance(condition, Relational):
        difference = condition.lhs - condition.rhs
        if condition.rel_op == '!=':
            return ~sp.Q.zero(difference)
        relation = condition.rel_op
        if difference.could_extract_minus_sign():
            difference = -difference
            relation = {'==': '==', '>': '<', '>=': '<=', '<': '>', '<=': '>='}[relation]
        query = {'==': sp.Q.zero, '>': sp.Q.positive,
                 '>=': sp.Q.nonnegative, '<': sp.Q.negative, '<=': sp.Q.nonpositive}[relation]
        return query(difference)
    if isinstance(condition, BooleanFunction):
        return condition.func(*(predicates(item) for item in condition.args))
    return condition


def validate_assumptions(condition):
    """Reject malformed statements and simple contradictions; do not claim completeness."""
    valid = condition in (sp.true, sp.false) or isinstance(condition, (Relational, BooleanFunction, AppliedPredicate, sp.Contains))
    if not valid:
        raise ValueError('Las hipótesis requieren relaciones, pertenencia a dominios o expresiones lógicas.')
    if condition is sp.false:
        raise ValueError('Hipótesis contradictorias.')
    converted = predicates(condition)
    try:
        if sp.satisfiable(converted) is False:
            raise ValueError('Hipótesis contradictorias.')
    except NotImplementedError:
        pass
    expanded = condition.replace(
        lambda item: (isinstance(item, sp.Contains) and isinstance(item.args[1], sp.Interval)
                      and item.args[1] != sp.S.Reals),
        lambda item: item.args[1].as_relational(item.args[0]),
    )
    parts = sp.And.make_args(expanded)
    relations = [part for part in parts if isinstance(part, Relational)]
    real_symbols = set()
    for part in sp.And.make_args(condition):
        if (isinstance(part, sp.Contains) and isinstance(part.args[0], sp.Symbol)
                and part.args[1] in (sp.S.Reals, sp.S.Integers)):
            real_symbols.add(part.args[0])
        elif isinstance(part, Relational) and not isinstance(part, (sp.Equality, sp.Unequality)):
            if isinstance(part.lhs, sp.Symbol) and part.rhs.is_real is True:
                real_symbols.add(part.lhs)
            if isinstance(part.rhs, sp.Symbol) and part.lhs.is_real is True:
                real_symbols.add(part.rhs)
        elif (isinstance(part, sp.Contains) and isinstance(part.args[0], sp.Symbol)
                and isinstance(part.args[1], sp.Interval)):
            real_symbols.add(part.args[0])
    # A bounded rational linear subsystem can prove inconsistency jointly,
    # rather than treating each predicate as an independent proposition.
    if len(relations) <= 32 and len(real_symbols) <= 8:
        linear = []
        for part in relations:
            symbols = sorted(part.free_symbols, key=sp.default_sort_key)
            if (not symbols or not set(symbols) <= real_symbols or sp.count_ops(part) > 64
                    or part.has(sp.oo, -sp.oo)):
                continue
            try:
                from .algebra import _rational_shape
                _rational_shape(part.lhs-part.rhs)
                polynomial = sp.Poly(part.lhs-part.rhs, *symbols, domain=sp.QQ)
                if polynomial.total_degree() <= 1:
                    linear.append(part)
            except (BasePolynomialError, ValueError, TypeError):
                continue
        if linear:
            inconsistent = False
            try:
                if sp.satisfiable(sp.And(*linear), use_lra_theory=True) is False:
                    inconsistent = True
            except (NotImplementedError, AssertionError, ValueError):
                pass
            if inconsistent:
                raise ValueError('Hipótesis contradictorias en el sistema lineal real.')
    equations = [part.lhs-part.rhs for part in relations if isinstance(part, sp.Equality)]
    symbols = sorted(set().union(*(item.free_symbols for item in equations)), key=sp.default_sort_key) if equations else []
    if equations and 1 <= len(symbols) <= 3 and len(equations) <= 4:
        inconsistent = False
        try:
            from .algebra import _rational_shape
            for expression in equations:
                _rational_shape(expression)
            polynomials = [sp.Poly(item, *symbols, domain=sp.QQ) for item in equations]
            if all(item.total_degree() <= 4 and len(item.terms()) <= 32
                   and all(max(abs(int(coefficient.p)).bit_length(), int(coefficient.q).bit_length()) <= 256
                           for coefficient in item.coeffs()) for item in polynomials):
                basis = sp.groebner([item.as_expr() for item in polynomials], *symbols, domain=sp.QQ)
                if any(item.as_expr() == 1 for item in basis.polys):
                    inconsistent = True
        except (BasePolynomialError, TypeError, NotImplementedError, ValueError):
            pass
        if inconsistent:
            raise ValueError('Hipótesis contradictorias en el sistema polinomial.')
    assignments = {}
    for part in relations:
        if isinstance(part, sp.Equality):
            if isinstance(part.lhs, sp.Symbol) and not part.rhs.free_symbols:
                symbol, value = part.lhs, part.rhs
            elif isinstance(part.rhs, sp.Symbol) and not part.lhs.free_symbols:
                symbol, value = part.rhs, part.lhs
            else:
                continue
            if symbol in assignments and sp.simplify(assignments[symbol] - value).is_zero is False:
                raise ValueError('Hipótesis contradictorias.')
            assignments[symbol] = value
    if assignments:
        for part in parts:
            if sp.simplify(part.xreplace(assignments)) is sp.false:
                raise ValueError('Hipótesis contradictorias.')
    for symbol in set().union(*(part.free_symbols for part in relations)) if relations else ():
        if symbol not in real_symbols:
            continue  # Ordering an expression (e.g. x**2) need not make x real.
        univariate = [part for part in relations if part.free_symbols <= {symbol}]
        if not univariate:
            continue
        try:
            reduced = sp.reduce_inequalities(univariate, symbol)
            if reduced is sp.false:
                raise ValueError('Hipótesis contradictorias.')
            integer_declared = any(isinstance(part, sp.Contains) and part.args == (symbol, sp.S.Integers)
                                   for part in sp.And.make_args(condition))
            if integer_declared and sp.Intersection(reduced.as_set(), sp.S.Integers).is_empty is True:
                raise ValueError('Hipótesis contradictorias: el intervalo no contiene enteros.')
        except (NotImplementedError, TypeError):
            pass
    # ask detects incompatible sign/domain predicates that propositional SAT cannot.
    for item in sp.And.make_args(converted):
        others = sp.And(*(part for part in sp.And.make_args(converted) if part != item))
        try:
            if sp.ask(item, others) is False:
                raise ValueError('Hipótesis contradictorias.')
        except (TypeError, NotImplementedError):
            pass
    return condition


def combine_assumptions(existing, new):
    return validate_assumptions(sp.And(existing, new))


def refine_expression(expression, assumptions):
    """Refine under explicit predicates without assigning properties to symbols."""
    if assumptions is sp.true or isinstance(expression, sp.Set):
        return expression
    try:
        return sp.refine(expression, predicates(assumptions))
    except (NotImplementedError, TypeError):
        return expression


def assumption_call(node, build, restrictions, state, bindings, functions, definitions):
    """Evaluate the supported hypothesis syntax within one local context."""
    def read(child):
        return build(child, restrictions, state, bindings, functions, definitions)

    name, children = node.value, node.children
    if name in ('And', 'Or', 'Not'):
        if (name == 'Not' and len(children) != 1) or (name != 'Not' and not children):
            raise ValueError(f'{name} tiene un número de argumentos incorrecto.')
        values = [read(child) for child in children]
        for value in values:
            if not (value in (sp.true, sp.false) or isinstance(value, (Relational, BooleanFunction, AppliedPredicate, sp.Contains))):
                raise ValueError('Los operadores lógicos requieren condiciones.')
        return {'And': sp.And, 'Or': sp.Or, 'Not': sp.Not}[name](*values)
    if name == 'Interval':
        if len(children) != 2:
            raise ValueError('Use Interval[mínimo,máximo], intervalo real cerrado.')
        lower, upper = [read(child) for child in children]
        if not all(isinstance(value, sp.Expr) and value.is_real is True and value.is_finite is True for value in (lower, upper)):
            raise ValueError('Interval requiere extremos reales finitos.')
        if (upper < lower) is sp.true:
            raise ValueError('Interval requiere extremos crecientes.')
        return sp.Interval(lower, upper)
    if name == 'Element':
        if len(children) != 2:
            raise ValueError('Use Element[expresión,dominio].')
        value, domain = [read(child) for child in children]
        if not isinstance(value, sp.Expr) or not isinstance(domain, sp.Set):
            raise ValueError('Element requiere una expresión escalar y un dominio.')
        return sp.Contains(value, domain)
    if name == 'With':
        if len(children) != 3 or children[0].kind != 'list' or children[1].kind != 'list':
            raise ValueError('Use With[{nombres},{valores},expresión].')
        names, values = children[:2]
        if len(names.children) != len(values.children) or len(names.children) > 64:
            raise ValueError('With requiere igual cantidad de nombres y valores (máximo 64).')
        if any(child.kind != 'name' for child in names.children):
            raise ValueError('With requiere nombres de variables.')
        from .session import PROTECTED_NAMES
        protected = PROTECTED_NAMES
        identifiers = [child.value for child in names.children]
        if len(set(identifiers)) != len(identifiers) or any(value in protected for value in identifiers):
            raise ValueError('With requiere nombres distintos y no protegidos.')
        evaluated = [read(child) for child in values.children]
        if any(not isinstance(value, sp.Expr) for value in evaluated):
            raise ValueError('With requiere valores escalares.')
        local = {**bindings, **dict(zip(identifiers, evaluated))}
        return build(children[2], restrictions, state, local, functions, definitions)
    if name in ('Assuming', 'Refine', 'Simplify'):
        if len(children) != 2:
            raise ValueError(f'{name} requiere dos argumentos en esta forma.')
        condition_node, expression_node = children if name == 'Assuming' else children[::-1]
        condition = read(condition_node)
        previous = getattr(state, 'assumptions', sp.true)
        combined = combine_assumptions(previous, condition)
        state.assumptions = combined
        try:
            value = read(expression_node)
            value = refine_expression(value, combined)
            if name == 'Simplify':
                value = sp.simplify(value)
        finally:
            state.assumptions = previous
        if condition is not sp.true:
            state.requirements.append(condition)
            state.conditions.append(sp.sstr(condition))
            state.mark_status('conditional')
            state.details['assumption_validation'] = 'simple contradictions checked; general consistency undecided'
        return value
    raise ValueError('Operación de hipótesis no admitida.')
