"""Certified rational enclosures for bounded exact real algebraic constants."""

import sympy as sp

from .calculus import OperationOutcome

MAX_CERTIFIED_DEGREE = 32
MAX_CERTIFIED_OPS = 64
MAX_COEFFICIENT_BITS = 4096


def _degree_bound(expression):
    if expression.is_Rational:
        if max(abs(int(expression.p)).bit_length(), int(expression.q).bit_length()) > MAX_COEFFICIENT_BITS:
            raise ValueError('Los coeficientes exactos exceden 4096 bits.')
        return 1
    if isinstance(expression, sp.CRootOf):
        return expression.poly.degree()
    if isinstance(expression, sp.AlgebraicNumber):
        return expression.minpoly.degree()
    if isinstance(expression, (sp.Add, sp.Mul)):
        bound = 1
        for item in expression.args:
            bound *= _degree_bound(item)
            if bound > MAX_CERTIFIED_DEGREE:
                raise ValueError('El grado algebraico estimado excede 32.')
        return bound
    if isinstance(expression, sp.Pow) and isinstance(expression.exp, sp.Rational):
        if abs(expression.exp.p) > 1024:
            raise ValueError('El exponente algebraico excede el límite.')
        return _degree_bound(expression.base) * int(expression.exp.q)
    if expression.func in (sp.sin, sp.cos) and len(expression.args) == 1:
        angle = sp.cancel(expression.args[0]/sp.pi)
        if isinstance(angle, sp.Rational):
            return 2 * int(angle.q)
    raise ValueError('CertifiedN no admite esta representación algebraica.')


def certified_numerical(expression, precision=30):
    """Return a rounded value and a rigorous rational bound on its absolute error.

    The certificate encloses the exact algebraic input, not uncertain measured
    data. Root identification uses the polynomial separation bound implemented
    by Poly.same_root; interval refinement uses rational polynomial isolation.
    """
    if isinstance(precision, bool) or not isinstance(precision, (int, sp.Integer)) or not 10 <= precision <= 200:
        raise ValueError('CertifiedN requiere una precisión entera entre 10 y 200.')
    precision = int(precision)
    if (not isinstance(expression, sp.Expr) or expression.free_symbols or expression.has(sp.Float)
            or expression.is_real is not True or expression.is_finite is not True
            or expression.is_algebraic is not True):
        raise ValueError('CertifiedN solo certifica constantes exactas algebraicas reales.')
    if sp.count_ops(expression) > MAX_CERTIFIED_OPS or _degree_bound(expression) > MAX_CERTIFIED_DEGREE:
        raise ValueError('CertifiedN excede el límite algebraico de 32 grados o 64 operaciones.')
    polynomial_text, root_index = None, None
    if isinstance(expression, sp.Rational):
        lower = upper = expression
        method = 'exact_rational_identity'
    else:
        variable = sp.Dummy('t')
        polynomial = sp.Poly(sp.minpoly(expression, variable), variable, domain=sp.QQ)
        if polynomial.degree() > MAX_CERTIFIED_DEGREE:
            raise ValueError('El polinomio mínimo excede grado 32.')
        if any(max(abs(int(coefficient.p)).bit_length(), int(coefficient.q).bit_length()) > MAX_COEFFICIENT_BITS
               for coefficient in polynomial.all_coeffs()):
            raise ValueError('El polinomio mínimo excede coeficientes de 4096 bits.')
        if polynomial.degree() == 1:
            lower = upper = -polynomial.nth(0)/polynomial.nth(1)
        else:
            roots = [root for root in polynomial.all_roots(radicals=False) if root.is_real is True]
            matches = [index for index, root in enumerate(roots) if polynomial.same_root(root, expression)]
            if len(matches) != 1:
                raise ValueError('No se pudo identificar de manera única la raíz algebraica real.')
            root_index = matches[0]
            coefficients = polynomial.all_coeffs()
            nonzero_lower = abs(coefficients[-1])/(abs(coefficients[-1]) + max(map(abs, coefficients[:-1])))
            epsilon = sp.Rational(1, 10)**(precision+5) * min(sp.S.One, nonzero_lower)
            intervals = polynomial.intervals(eps=epsilon, sqf=True)
            lower, upper = intervals[root_index]
            if polynomial.count_roots(lower, upper) != 1:
                raise ValueError('El intervalo no aisló una única raíz real.')
        polynomial_text = sp.sstr(polynomial.as_expr())
        method = 'exact_real_algebraic_polynomial_isolation'
    midpoint = (lower + upper)/2
    value = sp.Float(midpoint, precision)
    rounded = sp.Rational(value)
    absolute_bound = max(abs(rounded-lower), abs(rounded-upper))
    minimum_magnitude = min(abs(lower), abs(upper)) if lower*upper > 0 else sp.S.Zero
    relative_bound = absolute_bound/minimum_magnitude if minimum_magnitude else None
    return OperationOutcome(
        value, 'approximate', warnings=('La cota corresponde al valor algebraico exacto; no incluye incertidumbre de datos físicos.',),
        details={'method': method, 'certified': True, 'requested_significant_digits': precision,
                 'interval': {'lower': sp.sstr(lower), 'upper': sp.sstr(upper)},
                 'rounded_exact_rational': sp.sstr(rounded),
                 'absolute_error_bound': sp.sstr(absolute_bound),
                 'relative_error_bound': sp.sstr(relative_bound) if relative_bound is not None else None,
                 'minimal_polynomial': polynomial_text, 'real_root_index': root_index,
                 'verification': 'rational_enclosure_and_exact_rounding_distance'},
    )
