"""Real q-exponential and q-logarithm with explicit support conventions."""

import math

import sympy as sp
from sympy.core.evalf import prec_to_dps

from .assumptions import combine_assumptions, predicates
from .calculus import OperationOutcome


def _scalar(value):
    if type(value) in (int, float):
        value = sp.sympify(value)
    if (not isinstance(value, sp.Expr) or value.is_commutative is not True
            or value.is_real is False or value.is_finite is False
            or value.has(sp.nan, sp.zoo, sp.oo, -sp.oo)):
        raise ValueError("QExp y QLog requieren escalares reales finitos.")
    if sp.count_ops(value) > 256 or len(value.free_symbols) > 8:
        raise ValueError("El argumento excede 256 operaciones u ocho símbolos.")
    if any(abs(item._mpf_[2]) > 10000 or item._prec > 4096 for item in value.atoms(sp.Float)):
        raise ValueError("El dato aproximado excede el presupuesto de precisión o exponente.")
    if any(max(abs(int(item.p)).bit_length(), int(item.q).bit_length()) > 4096
           for item in value.atoms(sp.Rational)):
        raise ValueError("El argumento exacto excede 4096 bits por coeficiente.")
    return value


def _requirements(conditions, assumptions):
    result = []
    for condition in conditions:
        try:
            answer = sp.ask(predicates(condition), predicates(assumptions))
        except (TypeError, ValueError, NotImplementedError):
            answer = None
        if answer is False or condition is sp.false:
            raise ValueError("Los argumentos están fuera del dominio real de la función q.")
        if answer is not True and condition is not sp.true:
            result.append(condition)
    result = tuple(dict.fromkeys(result))
    combine_assumptions(assumptions, sp.And(*result))
    return result


def _power(base, exponent):
    # Avoid constructing gigantic exact powers before the result-size guard.
    if isinstance(base, sp.Rational) and isinstance(exponent, sp.Rational):
        bits = max(abs(int(base.p)).bit_length(), int(base.q).bit_length())
        if base not in (0, 1) and bits*abs(int(exponent.p)) > 12000:
            raise ValueError("La potencia exacta excede 12000 bits estimados; use argumentos N aproximados.")
    return base**exponent


def _formula(name, x, q):
    if (q-1).is_zero is True:
        return sp.exp(x) if name == "QExp" else sp.log(x)
    delta = 1-q
    if name == "QLog":
        general = (_power(x, delta)-1)/delta
    else:
        base = 1+delta*x
        if q.is_number and q < 1:
            if base.is_nonpositive is True:
                return sp.S.Zero
            general = _power(base, 1/delta)
            if base.is_positive is True:
                return general
            return sp.Piecewise((0, sp.Le(base, 0)), (general, True))
        general = _power(base, 1/delta)
        if not q.is_number:
            return sp.Piecewise((sp.exp(x), sp.Eq(q, 1)),
                                (0, sp.And(sp.Lt(q, 1), sp.Le(base, 0))),
                                (general, True))
    if q.is_number:
        return general
    return sp.Piecewise((sp.log(x), sp.Eq(q, 1)), (general, True))


def _loss_digits(value):
    if value == 0:
        return 0
    if isinstance(value, sp.Rational):
        return max(0, math.ceil((int(value.q).bit_length()-abs(int(value.p)).bit_length()+1)*math.log10(2)))
    return 0


def _numeric(name, x, q, atoms):
    digits = min(prec_to_dps(item._prec) for item in atoms)
    replace = {item: sp.Rational(item) for item in atoms}
    x, q = x.xreplace(replace), q.xreplace(replace)
    # The exact stored binary inputs are evaluated with enough guard digits to
    # keep cancellation at q=1 and x=1 out of the returned precision.
    working = digits+35+_loss_digits(1-q)+(_loss_digits(x-1) if name == "QLog" else 0)
    if working > 2000:
        raise ValueError("La cercanía al límite q requiere más de 2000 cifras de trabajo.")
    if q == 1:
        expression = sp.exp(x) if name == "QExp" else sp.log(x)
    elif name == "QExp":
        base = 1+(1-q)*x
        if q < 1 and base <= 0:
            return sp.Float(0, digits), digits
        expression = sp.exp(sp.log(base, evaluate=False)/(1-q), evaluate=False)
    else:
        exponent = (1-q)*sp.log(x, evaluate=False)
        expression = (sp.exp(exponent, evaluate=False)-1)/(1-q)
    value = expression.evalf(working, maxn=working*3).evalf(digits)
    if value.is_real is not True or value.is_finite is not True:
        raise ValueError("La evaluación numérica q no produjo un valor real finito.")
    if not isinstance(value, sp.Float):
        value = sp.Float(value, digits)
    if abs(value._mpf_[2]) > 10000 or value._prec > 4096:
        raise ValueError("El resultado aproximado excede el presupuesto de exponente o precisión.")
    return value, digits


def q_operation(name, args, assumptions=sp.true):
    """Return an ordinary SymPy expression and executable real-domain requirements."""
    if name not in {"QExp", "QLog"} or len(args) != 2:
        raise ValueError("Use QExp[x,q] o QLog[x,q].")
    x, q = map(_scalar, args)
    atoms = x.atoms(sp.Float) | q.atoms(sp.Float)
    numerical = bool(atoms) and not (x.free_symbols | q.free_symbols)
    exact_atoms = {item: sp.Rational(item) for item in atoms} if numerical else {}
    domain_x, domain_q = x.xreplace(exact_atoms), q.xreplace(exact_atoms)
    conditions = [sp.Contains(domain_x, sp.S.Reals), sp.Contains(domain_q, sp.S.Reals)]
    if name == "QLog":
        conditions.append(sp.Gt(domain_x, 0))
    else:
        conditions.append(sp.Or(sp.Le(domain_q, 1), sp.Gt(1+(1-domain_q)*domain_x, 0)))
    requirements = _requirements(conditions, assumptions)
    approximate = bool(atoms)
    digits = None
    if numerical:
        value, digits = _numeric(name, x, q, atoms)
    else:
        value = _formula(name, x, q)
    if sp.count_ops(value) > 4096:
        raise ValueError("El resultado q excede 4096 operaciones.")
    warnings = []
    if name == "QExp" and (not q.is_number or q < 1):
        warnings.append("En el corte de QExp, las derivadas formales por ramas no certifican una derivada en el punto de unión.")
    if approximate:
        warnings.append("La precisión numérica se refiere a los datos binarios almacenados; no certifica incertidumbre ni cotas rigurosas.")
    details = {"operation": name, "method": "real_q_function", "q_convention": "1+(1-q)*x",
               "domain": "finite_real", "precision_certified": False,
               "input_approximate": approximate,
               "support": "zero_cutoff_for_q_below_one_positive_base_for_q_above_one" if name == "QExp" else "strictly_positive_argument"}
    if digits is not None:
        details['requested_significant_digits'] = digits
    outcome = OperationOutcome(value, "conditional" if requirements else "evaluated",
                               tuple(map(sp.sstr, requirements)), tuple(warnings), details)
    return outcome, requirements
