"""Bounded conservative domains, retaining original exclusions and branch scope."""

import sympy as sp
from sympy.calculus.util import continuous_domain
from sympy.calculus.singularities import singularities

from .calculus import OperationOutcome

MAX_DOMAIN_OPS = 128
SUPPORTED_FUNCTIONS = {sp.sin, sp.cos, sp.exp, sp.log, sp.Abs, sp.asin, sp.acos, sp.atan}
NONPOSITIVE_INTEGERS = sp.Intersection(sp.S.Integers, sp.Interval(-sp.oo, 0))


def _domain(value):
    if value == 'Reals' or value is sp.S.Reals:
        return sp.S.Reals
    if value == 'Complexes' or value is sp.S.Complexes:
        return sp.S.Complexes
    raise ValueError('AnalyzeDomain admite Reals o Complexes.')


def _condition_set(condition, variable, domain):
    """Return an exact set only when the domain interpretation is justified."""
    if condition is sp.true:
        return domain, True
    if condition is sp.false:
        return sp.S.EmptySet, True
    if isinstance(condition, sp.Contains) and condition.args[0] == variable:
        return sp.Intersection(domain, condition.args[1]), True
    if isinstance(condition, (sp.And, sp.Or, sp.Not)):
        branches = [_condition_set(item, variable, domain) for item in condition.args]
        if all(decided for _, decided in branches):
            sets = [item for item, _ in branches]
            if isinstance(condition, sp.Not):
                return sp.Complement(domain, sets[0]), True
            return (sp.Intersection(*sets) if isinstance(condition, sp.And) else sp.Union(*sets)), True
        return sp.ConditionSet(variable, condition, domain), False
    if isinstance(condition, sp.Equality):
        result = sp.solveset(condition.lhs-condition.rhs, variable, domain=domain)
        return result, not result.has(sp.ConditionSet)
    if isinstance(condition, sp.Unequality):
        excluded = sp.solveset(condition.lhs-condition.rhs, variable, domain=domain)
        return sp.Complement(domain, excluded), not excluded.has(sp.ConditionSet)
    if domain is sp.S.Reals and condition.free_symbols <= {variable}:
        try:
            result = condition.as_set()
            return sp.Intersection(domain, result), not result.has(sp.ConditionSet)
        except (ValueError, TypeError, NotImplementedError):
            pass
    return sp.ConditionSet(variable, condition, domain), False


def analyze_domain(expression, variable, domain='Reals', restrictions=(), requirements=()):
    """Analyze real-valued continuity or a conservative complex finite-value set.

    Complex branch cuts are reported separately: a finite principal value on a
    cut does not establish analyticity there. No universal complex domain or
    automatic recovery of exclusions lost before this call is promised.
    """
    domain = _domain(domain)
    if (not isinstance(expression, sp.Expr) or not isinstance(variable, sp.Symbol)
            or expression.has(sp.nan, sp.zoo, sp.oo, -sp.oo)):
        raise ValueError('AnalyzeDomain requiere una expresión escalar finita y un símbolo.')
    if sp.count_ops(expression) > MAX_DOMAIN_OPS or len(expression.free_symbols) > 8:
        raise ValueError('AnalyzeDomain excede 128 operaciones u ocho símbolos.')
    conditions = list(requirements)
    conditions.extend(sp.Ne(item, 0) for item in restrictions)
    branches, warnings = [], []
    complete = True
    extra_parameters = expression.free_symbols - {variable}
    gamma_direct = expression.func is sp.gamma and expression.args == (variable,)
    unsupported = any(item.func not in SUPPORTED_FUNCTIONS and item.func is not sp.gamma
                      for item in expression.atoms(sp.Function))
    if gamma_direct:
        result = sp.Complement(domain, NONPOSITIVE_INTEGERS)
    elif unsupported or expression.has(sp.gamma) or extra_parameters:
        result = sp.ConditionSet(variable, sp.Contains(expression, domain), domain)
        complete = False
        warnings.append('No se ha determinado completamente el dominio de esta función o sus parámetros.')
    elif domain is sp.S.Reals:
        try:
            result = continuous_domain(expression, variable, domain)
            complete = not result.has(sp.ConditionSet)
        except (ValueError, TypeError, NotImplementedError):
            result = sp.ConditionSet(variable, sp.Contains(expression, domain), domain)
            complete = False
        # SymPy's continuous_domain accepts real odd roots of negatives. Here
        # noninteger powers retain the principal complex-power convention.
        for power in expression.atoms(sp.Pow):
            if isinstance(power.exp, sp.Rational) and power.exp.q != 1:
                conditions.append(sp.Ge(power.base, 0) if power.exp > 0 else sp.Gt(power.base, 0))
    else:
        try:
            excluded = singularities(expression, variable, domain)
            result = sp.Complement(domain, excluded)
            complete = not excluded.has(sp.ConditionSet)
        except (ValueError, TypeError, NotImplementedError):
            result = sp.ConditionSet(variable, sp.Contains(expression, domain), domain)
            complete = False
        for function in expression.atoms(sp.Function):
            if function.func is sp.log:
                branches.append({'function': 'Log', 'argument': sp.sstr(function.args[0]),
                                 'cut_in_argument_plane': 'negative real axis; branch point 0'})
            elif function.func in (sp.asin, sp.acos):
                branches.append({'function': sp.sstr(function.func), 'argument': sp.sstr(function.args[0]),
                                 'cut_in_argument_plane': 'real rays (-infinity,-1] and [1,infinity)'})
            elif function.func is sp.atan:
                conditions.append(sp.Ne(1+function.args[0]**2,0))
                branches.append({'function': 'ArcTan', 'argument': sp.sstr(function.args[0]),
                                 'cut_in_argument_plane': 'imaginary rays from +i and -i toward infinity'})
        for power in expression.atoms(sp.Pow):
            if isinstance(power.exp, sp.Rational) and power.exp.q != 1:
                branches.append({'function': 'principal rational power', 'argument': sp.sstr(power.base),
                                 'cut_in_argument_plane': 'negative real axis; branch point 0'})
        if branches:
            complete = False
            warnings.append('Los cortes se describen en el plano del argumento; no se ha calculado su preimagen ni el dominio holomorfo completo.')
    for condition in conditions:
        if not isinstance(condition, sp.Basic):
            raise ValueError('Las condiciones de dominio deben ser expresiones simbólicas.')
        try:
            admissible, decided = _condition_set(condition, variable, domain)
            result = sp.Intersection(result, admissible)
            complete = complete and decided
        except (ValueError, TypeError, NotImplementedError):
            result = sp.ConditionSet(variable, condition, result)
            complete = False
    details = {'method': 'bounded_conservative_domain_analysis', 'variable': str(variable),
               'domain': sp.sstr(domain), 'complete': bool(complete),
               'scope': 'real_valued_continuity' if domain is sp.S.Reals else 'complex_finite_values_not_global_analyticity',
               'branch_cuts': branches, 'original_exclusions_retained': len(restrictions),
               'requirements_retained': len(requirements)}
    return OperationOutcome(result, 'evaluated' if complete else 'unresolved',
                            warnings=tuple(warnings), details=details)
