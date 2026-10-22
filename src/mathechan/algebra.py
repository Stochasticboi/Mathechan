"""Exact scalar algebra over Q and explicitly requested numerical evaluation.

Factor accepts polynomials over Q. Together and Cancel accept rational functions
over Q in up to eight commuting symbols; they are not general simplifiers.
Transcendental functions, irrational coefficients, and Float coefficients are
outside this initial algebraic scope. Original domain restrictions must be kept
by the caller: an already cancelled expression cannot recover its provenance.
"""

from math import comb

import sympy as sp
from sympy.core.evalf import PrecisionExhausted

MAX_SYMBOLS = 8
MAX_DEGREE = 256
MAX_TERMS = 4096


def _scalar(expression):
    """Accept constructed scalar expressions, never parse or evaluate strings."""
    if not isinstance(expression, sp.Expr) or expression.is_commutative is not True:
        raise ValueError("Se requiere una expresión escalar conmutativa de SymPy.")
    held_or_conditional = expression.has(sp.Integral, sp.Piecewise)
    if expression.is_finite is False or (
        expression.has(sp.oo, -sp.oo, sp.zoo, sp.nan) and not held_or_conditional
    ):
        raise ValueError("La expresión no puede ser infinita ni estar indefinida.")
    return expression


def numerical(expression, precision=15):
    """Approximate a finite numeric scalar using strict decimal precision.

    Precision is an integer from 1 to 1000. Existing approximate inputs retain
    their original information; asking for more digits cannot recover lost data.
    Real results, including zero and integers, remain Float rather than Rational.
    Complex results retain numerical real/imaginary parts.
    """
    expression = _scalar(expression)
    if isinstance(precision, bool) or not isinstance(precision, (int, sp.Integer)):
        raise ValueError("La precisión debe ser un entero entre 1 y 1000.")  # noqa: TRY004 - uniform backend validation contract
    precision = int(precision)
    if not 1 <= precision <= 1000:
        raise ValueError("La precisión debe ser un entero entre 1 y 1000.")
    if expression.free_symbols or expression.is_number is not True:
        raise ValueError("N requiere una expresión numérica sin símbolos libres.")
    try:
        result = expression.evalf(precision, strict=True)
    except PrecisionExhausted as error:
        raise ValueError(
            "N no pudo certificar la precisión solicitada; simplifique la "
            "expresión exacta o revise sus cancelaciones."
        ) from error
    except (ArithmeticError, TypeError, NotImplementedError) as error:
        raise ValueError(
            "No se pudo obtener una aproximación numérica finita."
        ) from error
    _scalar(result)
    if result.is_number is not True or result.is_finite is not True:
        raise ValueError("No se obtuvo una aproximación numérica finita.")
    return sp.Float(result, precision) if isinstance(result, sp.Rational) else result


def _bounded_shape(
    numerator_terms, numerator_degree, denominator_terms, denominator_degree
):
    if max(numerator_terms, denominator_terms) > MAX_TERMS:
        raise ValueError("La expansión estimada excede 4096 términos.")
    if max(numerator_degree, denominator_degree) > MAX_DEGREE:
        raise ValueError("El grado algebraico excede 256.")
    return numerator_terms, numerator_degree, denominator_terms, denominator_degree


def _power_term_bound(terms, power):
    # Commuting products differ only by multiplicities of the original terms.
    return comb(terms + power - 1, power)


def _rational_shape(expression):
    """Bound potential numerator/denominator expansion before polynomial work.

    Counts are conservative upper bounds, not promises of execution time.
    The restricted expression grammar also verifies rational coefficients.
    """
    if isinstance(expression, sp.Rational):
        return 1, 0, 1, 0
    if isinstance(expression, sp.Symbol):
        return 1, 1, 1, 0
    if isinstance(expression, sp.Pow):
        exponent = expression.exp
        if not isinstance(exponent, sp.Integer) or abs(exponent) > MAX_DEGREE:
            raise ValueError("Solo se admiten potencias enteras de grado hasta 256.")
        nt, nd, dt, dd = _rational_shape(expression.base)
        power = abs(int(exponent))
        shape = _bounded_shape(
            _power_term_bound(nt, power),
            nd * power,
            _power_term_bound(dt, power),
            dd * power,
        )
        return (shape[2], shape[3], shape[0], shape[1]) if exponent < 0 else shape
    if isinstance(expression, (sp.Add, sp.Mul)):
        arguments = iter(expression.args)
        total = _rational_shape(next(arguments))
        for item in arguments:
            nt, nd, dt, dd = total
            at, ad, bt, bd = _rational_shape(item)
            if isinstance(expression, sp.Add):
                total = _bounded_shape(
                    nt * bt + at * dt, max(nd + bd, ad + dd), dt * bt, dd + bd
                )
            else:
                total = _bounded_shape(nt * at, nd + ad, dt * bt, dd + bd)
        return total
    raise ValueError(
        "Se requiere álgebra racional sobre Q: sin Float, funciones ni "
        "coeficientes irracionales."
    )


def _rational_expression(expression, polynomial=False):
    expression = _scalar(expression)
    if len(expression.free_symbols) > MAX_SYMBOLS:
        raise ValueError("Se admiten como máximo ocho símbolos en álgebra racional.")
    shape = _rational_shape(expression)
    if polynomial and shape[3] != 0:
        raise ValueError("Factor requiere un polinomio con coeficientes racionales.")
    return expression


def factor_expression(expression):
    """Factor a bounded multivariate polynomial over rational coefficients."""
    expression = _rational_expression(expression, polynomial=True)
    return sp.factor(expression, domain=sp.QQ)


def together_expression(expression):
    """Combine rational functions over Q without promising cancellation."""
    expression = _rational_expression(expression)
    return sp.together(expression)


def cancel_expression(expression):
    """Cancel rational polynomial factors; caller retains original exclusions."""
    expression = _rational_expression(expression)
    return sp.cancel(expression, domain=sp.QQ)


def collect_expression(expression, symbol):
    """Collect a bounded polynomial over Q by powers of one explicit variable."""
    expression = _rational_expression(expression, polynomial=True)
    if not isinstance(symbol, sp.Symbol) or symbol.is_commutative is not True:
        raise ValueError("Collect requiere un símbolo escalar como variable.")
    return sp.collect(sp.expand(expression), symbol)


def apart_expression(expression, symbol):
    """Partial fractions in one variable, retaining symbolic rational parameters."""
    expression = _rational_expression(expression)
    if not isinstance(symbol, sp.Symbol) or symbol.is_commutative is not True:
        raise ValueError("Apart requiere un símbolo escalar como variable.")
    return sp.apart(expression, symbol)


def apart_parameter_branches(expression, symbol, result):
    """Cover a single affine parameter degeneracy; leave larger cases explicit."""
    factors = set()
    for term in sp.Add.make_args(result):
        for factor, _ in sp.factor_list(term.as_numer_denom()[1])[1]:
            if factor.free_symbols and symbol not in factor.free_symbols:
                factors.add(factor)
    if len(factors) != 1:
        return result, ()
    factor = next(iter(factors))
    if len(factor.free_symbols) != 1:
        return result, ()
    parameter = next(iter(factor.free_symbols))
    polynomial = sp.Poly(factor, parameter)
    if polynomial.degree() != 1:
        return result, ()
    special_value = -polynomial.nth(0) / polynomial.nth(1)
    special = expression.subs(parameter, special_value)
    if special.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
        return result, ()
    special = apart_expression(special, symbol)
    condition = sp.Ne(parameter, special_value)
    branches = (
        {"condition": sp.sstr(condition), "value": sp.sstr(result)},
        {"condition": sp.sstr(sp.Eq(parameter, special_value)), "value": sp.sstr(special)},
    )
    return sp.Piecewise((result, condition), (special, True), evaluate=False), branches


def substitute_expression(expression, symbol, value):
    """Perform one exact simultaneous substitution on constructed scalars.

    Other symbols and their assumptions remain distinct. This operation does
    not undo upstream simplification or enforce the caller's domain conditions.
    """
    expression = _scalar(expression)
    if not isinstance(symbol, sp.Symbol) or symbol.is_commutative is not True:
        raise ValueError("Substitute requiere un símbolo escalar como variable.")
    value = _scalar(value)
    result = expression.subs(symbol, value, simultaneous=True)
    if result.has(sp.Integral) and result != expression:
        result = result.doit()
    return _scalar(result)
