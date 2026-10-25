"""Validated scalar probability families with explicit parameter conventions."""

import sympy as sp
from sympy.core.symbol import Str
from sympy.functions.combinatorial.numbers import stirling

from .assumptions import combine_assumptions, predicates
from .calculus import OperationOutcome
from .finite_probability import _scalar

FAMILY_ARITIES = {
    "BinomialDistribution": 2, "PoissonDistribution": 1,
    "NormalDistribution": 2, "ExponentialDistribution": 1,
    "GammaDistribution": 2,
}


def _parameter_conditions(family, parameters):
    conditions = [sp.Contains(value, sp.S.Reals) for value in parameters]
    if family == "BinomialDistribution":
        n, p = parameters
        conditions.extend((sp.Contains(n, sp.S.Integers), sp.Ge(n, 0), sp.Ge(p, 0), sp.Le(p, 1)))
    elif family == "PoissonDistribution":
        conditions.append(sp.Ge(parameters[0], 0))
    elif family == "NormalDistribution":
        conditions.append(sp.Gt(parameters[1], 0))
    else:
        conditions.extend(sp.Gt(value, 0) for value in parameters)
    if any(condition is sp.false for condition in conditions):
        raise ValueError("Parámetros fuera del dominio de la distribución.")
    return tuple(dict.fromkeys(condition for condition in conditions if condition is not sp.true))


class ParametricDistribution(sp.Basic):
    """A named family and scalar parameters; no executable source is retained."""

    def __new__(cls, family, parameters):
        family = str(family)
        if family not in FAMILY_ARITIES or not isinstance(parameters, (tuple, list, sp.Tuple)):
            raise ValueError("Familia o parámetros de distribución no admitidos.")
        if len(parameters) != FAMILY_ARITIES[family]:
            raise ValueError("Número de parámetros incorrecto para la distribución.")
        values = sp.Tuple(*(_scalar(value) for value in parameters))
        if (sum(int(sp.count_ops(value)) for value in values) > 256 or
                len(set().union(*(value.free_symbols for value in values))) > 8):
            raise ValueError("La distribución excede ocho símbolos o 256 operaciones de entrada.")
        _parameter_conditions(family, values)
        return sp.Basic.__new__(cls, Str(family), values)

    @property
    def family(self):
        return str(self.args[0])

    @property
    def parameters(self):
        return self.args[1]

    @property
    def is_discrete(self):
        return self.family in {"BinomialDistribution", "PoissonDistribution"}

    def _sympystr(self, printer):
        return self.family + "[" + ",".join(printer.doprint(value) for value in self.parameters) + "]"


def _requirements(conditions, assumptions):
    result = []
    for condition in conditions:
        if condition is sp.false:
            raise ValueError("El cálculo viola una condición de la distribución.")
        try:
            answer = sp.ask(predicates(condition), predicates(assumptions))
        except (ValueError, TypeError, NotImplementedError):
            answer = None
        condition = sp.true if answer is True else sp.false if answer is False else condition
        combine_assumptions(assumptions, condition)
        if condition is not sp.true:
            result.append(condition)
    return tuple(dict.fromkeys(result))


def parametric_requirements(distribution, assumptions=sp.true):
    if not isinstance(distribution, ParametricDistribution):
        raise ValueError("Se requiere una distribución paramétrica escalar.")
    return _requirements(_parameter_conditions(distribution.family, distribution.parameters), assumptions)


def _point(value, infinity=False):
    if infinity and value in (sp.oo, -sp.oo):
        return value
    return _scalar(value)


def _degenerate_point(distribution):
    family, parameters = distribution.family, distribution.parameters
    if family == "PoissonDistribution" and parameters[0].is_zero is True:
        return sp.S.Zero
    if family == "BinomialDistribution":
        n, p = parameters
        if n.is_zero is True or p.is_zero is True:
            return sp.S.Zero
        if (p-1).is_zero is True:
            return n
    return None


def parametric_support(distribution):
    parametric_requirements(distribution)
    point = _degenerate_point(distribution)
    if point is not None:
        return sp.FiniteSet(point)
    family, parameters = distribution.family, distribution.parameters
    if family == "NormalDistribution":
        return sp.S.Reals
    if not distribution.is_discrete:
        return sp.Interval(0, sp.oo)
    k = sp.Dummy("k", integer=True, nonnegative=True)
    if family == "BinomialDistribution":
        n, p = parameters
        base = sp.Range(0, n+1)
        if p.is_positive is True and (1-p).is_positive is True:
            return base
    else:
        base = sp.S.Naturals0
        if parameters[0].is_positive is True:
            return base
    return sp.ConditionSet(k, sp.Gt(parametric_density(distribution, k), 0), base)


def parametric_density(distribution, x):
    """Return a probability mass or density; Gamma uses shape and scale."""
    parametric_requirements(distribution)
    x = _point(x, infinity=True)
    if x in (sp.oo, -sp.oo):
        return sp.S.Zero
    point = _degenerate_point(distribution)
    if point is not None:
        return sp.Piecewise((1, sp.Eq(x, point)), (0, True))
    family, parameters = distribution.family, distribution.parameters
    if family == "BinomialDistribution":
        n, p = parameters
        mass = sp.binomial(n, x)*p**x*(1-p)**(n-x)
        return sp.Piecewise((mass, sp.And(sp.Contains(x, sp.S.Integers), x >= 0, x <= n)), (0, True))
    if family == "PoissonDistribution":
        rate, = parameters
        mass = sp.exp(-rate)*rate**x/sp.factorial(x)
        return sp.Piecewise((mass, sp.And(sp.Contains(x, sp.S.Integers), x >= 0)), (0, True))
    if family == "NormalDistribution":
        mean, sigma = parameters
        return sp.exp(-(x-mean)**2/(2*sigma**2))/(sp.sqrt(2*sp.pi)*sigma)
    if family == "ExponentialDistribution":
        rate, = parameters
        return sp.Piecewise((rate*sp.exp(-rate*x), x >= 0), (0, True))
    shape, scale = parameters
    # At x=0 the density has a finite value only for shape >=1. Its value
    # at a single point never changes the continuous probability measure.
    boundary = sp.Piecewise((sp.oo, shape < 1), (1/scale, sp.Eq(shape, 1)), (0, True))
    if x.is_zero is True:
        return boundary
    density = x**(shape-1)*sp.exp(-x/scale)/(sp.gamma(shape)*scale**shape)
    return sp.Piecewise((boundary, sp.Eq(x, 0)), (density, x > 0), (0, True))


def _cdf(distribution, x):
    if x is -sp.oo:
        return sp.S.Zero
    if x is sp.oo:
        return sp.S.One
    point = _degenerate_point(distribution)
    if point is not None:
        return sp.Piecewise((0, x < point), (1, True))
    family, parameters = distribution.family, distribution.parameters
    if family == "NormalDistribution":
        mean, sigma = parameters
        return (1+sp.erf((x-mean)/(sp.sqrt(2)*sigma)))/2
    if family == "ExponentialDistribution":
        rate, = parameters
        return sp.Piecewise((0, x < 0), (1-sp.exp(-rate*x), True))
    if family == "GammaDistribution":
        shape, scale = parameters
        return sp.Piecewise((0, x <= 0), (sp.lowergamma(shape, x/scale)/sp.gamma(shape), True))
    if family == "PoissonDistribution":
        rate, = parameters
        value = sp.uppergamma(sp.floor(x)+1, rate)/sp.gamma(sp.floor(x)+1)
        return sp.Piecewise((0, x < 0), (value, True))
    n, p = parameters
    k = sp.Dummy("k", integer=True, nonnegative=True)
    upper = sp.floor(x)
    if upper.is_Integer and 0 <= upper <= 128:
        value = sp.Add(*(sp.binomial(n, j)*p**j*(1-p)**(n-j) for j in range(int(upper)+1)))
    else:
        value = sp.Sum(sp.binomial(n, k)*p**k*(1-p)**(n-k), (k, 0, upper))
    return sp.Piecewise((0, x < 0), (1, x >= n), (value, True))


def parametric_cdf(distribution, x):
    """Right-continuous cumulative probability, including infinite limits."""
    parametric_requirements(distribution)
    return _cdf(distribution, _point(x, infinity=True))


def parametric_raw_moment(distribution, n):
    """E[X**n] for exact integer orders0..12, using finite formulas."""
    parametric_requirements(distribution)
    if type(n) is int:
        n = sp.Integer(n)
    if not isinstance(n, sp.Integer) or not 0 <= n <= 12:
        raise ValueError("El orden del momento debe ser un entero exacto entre cero y doce.")
    if n == 0:
        return sp.S.One
    family, parameters = distribution.family, distribution.parameters
    if family == "PoissonDistribution":
        return sp.Add(*(stirling(n, k, kind=2)*parameters[0]**k for k in range(1, int(n)+1)))
    if family == "BinomialDistribution":
        trials, p = parameters
        return sp.Add(*(stirling(n, k, kind=2)*sp.ff(trials, k)*p**k for k in range(1, int(n)+1)))
    if family == "NormalDistribution":
        mean, sigma = parameters
        return sp.Add(*(sp.binomial(n, 2*k)*sp.factorial2(2*k-1)*sigma**(2*k)*mean**(n-2*k)
                        for k in range(int(n)//2+1)))
    if family == "ExponentialDistribution":
        return sp.factorial(n)/parameters[0]**n
    shape, scale = parameters
    return sp.rf(shape, n)*scale**n


def parametric_transform(distribution, t, characteristic=False):
    """MGF on its real convergence interval, or CF for all real arguments."""
    parametric_requirements(distribution)
    t = _scalar(t)
    requirements = [sp.Contains(t, sp.S.Reals)]
    argument = sp.I*t if characteristic else t
    family, parameters = distribution.family, distribution.parameters
    if family == "BinomialDistribution":
        n, p = parameters
        value = (1-p+p*sp.exp(argument))**n
    elif family == "PoissonDistribution":
        value = sp.exp(parameters[0]*(sp.exp(argument)-1))
    elif family == "NormalDistribution":
        mean, sigma = parameters
        value = sp.exp(mean*argument+sigma**2*argument**2/2)
    elif family == "ExponentialDistribution":
        rate, = parameters
        value = rate/(rate-argument)
        if not characteristic:
            requirements.append(t < rate)
    else:
        shape, scale = parameters
        value = (1-scale*argument)**(-shape)
        if not characteristic:
            requirements.append(t < 1/scale)
    requirements = tuple(condition for condition in requirements if condition is not sp.true)
    if any(condition is sp.false for condition in requirements):
        raise ValueError("El argumento queda fuera del dominio de convergencia de la transformada.")
    return value, requirements


def _entropy(distribution):
    point = _degenerate_point(distribution)
    if point is not None:
        return sp.S.Zero
    family, parameters = distribution.family, distribution.parameters
    if family == "NormalDistribution":
        return sp.log(2*sp.pi*sp.E*parameters[1]**2)/2
    if family == "ExponentialDistribution":
        return 1-sp.log(parameters[0])
    if family == "GammaDistribution":
        shape, scale = parameters
        return shape+sp.log(scale)+sp.loggamma(shape)+(1-shape)*sp.polygamma(0, shape)
    k = sp.Dummy("k", integer=True, nonnegative=True)
    if family == "BinomialDistribution":
        n, p = parameters
        if n.is_Integer and n <= 64:
            masses = [parametric_density(distribution, sp.Integer(j)) for j in range(int(n)+1)]
            return sp.simplify(sp.Add(*(sp.Piecewise((0, sp.Eq(mass, 0)), (-mass*sp.log(mass), True))
                                       for mass in masses)))
        mass = sp.binomial(n, k)*p**k*(1-p)**(n-k)
        upper = n
    else:
        rate, = parameters
        mass = sp.exp(-rate)*rate**k/sp.factorial(k)
        upper = sp.oo
    return sp.Sum(sp.Piecewise((0, sp.Eq(mass, 0)), (-mass*sp.log(mass), True)), (k, 0, upper))


def parametric_operation(name, args, assumptions=sp.true):
    """Construct or query one scalar family, with executable requirements."""
    extra = ()
    if name in FAMILY_ARITIES:
        value = distribution = ParametricDistribution(name, args)
    else:
        if not args or not isinstance(args[0], ParametricDistribution):
            raise ValueError("Se requiere una distribución paramétrica.")
        distribution = args[0]
        count = 2 if name in {"PDF", "CDF"} else 1
        if len(args) != count:
            raise ValueError("Número de argumentos incorrecto para la operación.")
        if name in {"PDF", "CDF"}:
            x = _point(args[1], infinity=True)
            extra = () if x in (sp.oo, -sp.oo) else (sp.Contains(x, sp.S.Reals),)
            value = parametric_density(distribution, x) if name == "PDF" else _cdf(distribution, x)
        elif name == "Support":
            value = parametric_support(distribution)
        elif name == "Mean":
            value = parametric_raw_moment(distribution, 1)
        elif name in {"Variance", "StandardDeviation"}:
            parameters = distribution.parameters
            if distribution.family == "BinomialDistribution":
                n, p = parameters
                value = n*p*(1-p)
            elif distribution.family == "PoissonDistribution":
                value = parameters[0]
            elif distribution.family == "NormalDistribution":
                value = parameters[1]**2
            elif distribution.family == "ExponentialDistribution":
                value = 1/parameters[0]**2
            else:
                value = parameters[0]*parameters[1]**2
            if name == "StandardDeviation":
                value = sp.sqrt(value)
        elif name == "Entropy":
            value = _entropy(distribution)
        else:
            raise ValueError("Operación desconocida para una distribución paramétrica.")
    requirements = _requirements((*parametric_requirements(distribution, assumptions), *extra), assumptions)
    if int(sp.count_ops(value)) > 4096:
        raise ValueError("El resultado excede 4096 operaciones.")
    pending = value.has(sp.Sum, sp.Integral)
    nonfinite = value.has(sp.oo, -sp.oo, sp.zoo, sp.nan) and name != "Support" and name not in FAMILY_ARITIES
    possible_divergence = nonfinite and isinstance(value, sp.Piecewise)
    divergent = nonfinite and not possible_divergence
    status = ("unresolved" if pending else "divergent" if divergent else
              "conditional" if requirements or possible_divergence else "evaluated")
    warnings = []
    if distribution.has(sp.Float):
        warnings.append("Los datos aproximados no certifican precisión ni incertidumbre física; no se usa tolerancia para validar parámetros.")
    if pending:
        warnings.append("La suma exacta queda pendiente; no se presenta como valor numérico calculado.")
    if possible_divergence:
        warnings.append("La densidad diverge para algunas ramas de parámetros; no es una masa de probabilidad.")
    details = {"operation": name, "method": "analytic_probability_family", "family": distribution.family,
               "measure": "discrete_probability_mass" if distribution.is_discrete else "continuous_density",
               "precision_certified": False, "sympy_version": sp.__version__}
    if name == "Entropy":
        details.update(entropy_units="nats", entropy_kind="Shannon" if distribution.is_discrete else "differential")
    return OperationOutcome(value, status, tuple(map(sp.sstr, requirements)), tuple(warnings), details), requirements
