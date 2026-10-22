"""Conservative bounded simplification with explicit equivalence checks."""

import sympy as sp

from .assumptions import combine_assumptions, refine_expression
from .calculus import OperationOutcome
from .algebra import _rational_shape

MAX_SIMPLIFY_OPS = 256
MAX_SIMPLIFY_SYMBOLS = 8


def full_simplify_expression(expression, assumptions=sp.true, restrictions=(), requirements=()):
    """Choose a smaller verified candidate; never force branches or discard provenance."""
    if (not isinstance(expression, sp.Expr) or expression.is_commutative is not True
            or expression.has(sp.nan, sp.zoo, sp.oo, -sp.oo)):
        raise ValueError('FullSimplify requiere una expresión escalar finita.')
    if sp.count_ops(expression) > MAX_SIMPLIFY_OPS or len(expression.free_symbols) > MAX_SIMPLIFY_SYMBOLS:
        raise ValueError('FullSimplify excede el límite de 256 operaciones u ocho símbolos.')
    # Bound algebraic expansion before calling transformations that can expand
    # products or powers. Functions and nonintegral powers are opaque atoms.
    opaque = {item: sp.Dummy() for item in sp.preorder_traversal(expression)
              if item.is_Function or (isinstance(item, sp.Pow) and not item.exp.is_Integer)
              or (item.is_Atom and not isinstance(item, (sp.Symbol, sp.Rational)))}
    _rational_shape(expression.xreplace(opaque))
    for item in sp.preorder_traversal(expression):
        if isinstance(item, sp.Pow) and item.exp.is_Integer:
            _rational_shape(item.xreplace(opaque))
    context = combine_assumptions(assumptions, sp.And(*requirements))
    source = refine_expression(expression, context)
    candidates = [('original', source)]
    for method, operation in [('simplify', sp.simplify), ('together', sp.together),
                              ('cancel', sp.cancel), ('trigsimp', sp.trigsimp)]:
        try:
            candidate = refine_expression(operation(source), context)
            if sp.count_ops(candidate) <= MAX_SIMPLIFY_OPS:
                difference = refine_expression(sp.simplify(candidate-source), context)
                if difference == 0:
                    candidates.append((method, candidate))
        except (ValueError, TypeError, NotImplementedError, ArithmeticError):
            continue
    method, value = min(candidates, key=lambda item: (sp.count_ops(item[1]), len(sp.sstr(item[1]))))
    conditions = [sp.sstr(context)] if context is not sp.true else []
    conditions.extend(f'({sp.sstr(item)}) != 0' for item in restrictions)
    return OperationOutcome(
        value, 'conditional' if conditions else 'evaluated', tuple(dict.fromkeys(conditions)),
        ('La búsqueda de simplificación es acotada; no garantiza una forma mínima universal.',),
        {'method': 'bounded_verified_simplification', 'selected_transform': method,
         'verification': 'symbolic_equivalence_in_explicit_context',
         'candidate_count': len(candidates), 'input_operations': int(sp.count_ops(expression)),
         'output_operations': int(sp.count_ops(value))},
    )
