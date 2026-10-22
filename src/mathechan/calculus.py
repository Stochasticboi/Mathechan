"""Bounded symbolic integration, algebraic solving, and single-function ODEs.

Backend contracts follow the SymPy 1.14 integral, solveset/linsolve, and
dsolve/checkodesol documentation. No parser or session state is imported here.
"""

from dataclasses import dataclass, field

import sympy as sp
from sympy.core.function import AppliedUndef
from sympy.solvers.solveset import NonlinearError


@dataclass(frozen=True)
class OperationOutcome:
    value: sp.Basic
    status: str = "evaluated"
    conditions: tuple = ()
    warnings: tuple = ()
    details: dict = field(default_factory=dict)


def _symbol(variable):
    if not isinstance(variable, sp.Symbol):
        raise ValueError("La variable debe ser un símbolo.")  # noqa: TRY004 - uniform backend validation contract
    return variable


def _expression(expression):
    if not isinstance(expression, sp.Expr) or expression.has(
        sp.nan, sp.zoo, sp.oo, -sp.oo
    ):
        raise ValueError(
            "Se requiere una expresión simbólica finita, no una ecuación o lista."
        )
    return expression


def _details(method, **extra):
    return {"method": method, "sympy_version": sp.__version__, **extra}


def integrate_expression(expr, variable, bounds=None):
    """Keep conditional branches; an indefinite result omits the additive constant."""
    expr, variable = _expression(expr), _symbol(variable)
    warnings, conditions = [], []
    if bounds is None:
        argument = variable
        warnings.append("La constante aditiva de integración no está incluida.")
    else:
        if not isinstance(bounds, (list, tuple, sp.Tuple)) or len(bounds) != 2:
            raise ValueError("Los límites deben ser un par (mínimo, máximo).")
        for bound in bounds:
            if (
                not isinstance(bound, sp.Expr)
                or bound.has(variable)
                or bound.is_extended_real is False
            ):
                raise ValueError(
                    "Los límites deben ser reales, independientes de la variable; se admiten infinitos reales."
                )
            if bound.has(sp.nan, sp.zoo):
                raise ValueError("El límite está indefinido.")
            if bound.is_extended_real is None:
                conditions.append(
                    f"Límite real: {sp.sstr(sp.Contains(bound, sp.S.Reals))}"
                )
        argument = (variable, *bounds)
    result = sp.integrate(expr, argument, conds="piecewise")
    if not isinstance(result, sp.Basic):
        raise ValueError("El integrador no devolvió una expresión simbólica.")  # noqa: TRY004 - uniform backend validation contract
    branches = result.atoms(sp.Piecewise)
    if not branches and result.has(sp.oo, -sp.oo, sp.zoo, sp.nan, sp.AccumBounds):
        raise ValueError(
            "La integral diverge o no tiene un límite convergente; no se ha pedido valor principal."
        )
    if branches:
        warnings.append(
            "Las condiciones de Piecewise corresponden a ramas alternativas, no a requisitos simultáneos."
        )
        for piecewise in sorted(branches, key=sp.default_sort_key):
            for index, (_, condition) in enumerate(piecewise.args, 1):
                if condition is not sp.S.true:
                    conditions.append(
                        f"Condición de rama {index}: {sp.sstr(condition)}"
                    )
        if result.has(sp.oo, -sp.oo, sp.zoo, sp.nan, sp.AccumBounds):
            warnings.append(
                "El resultado conserva ramas divergentes; no es un valor finito incondicional."
            )
    unresolved = result.has(sp.Integral)
    verification = "not_checked"
    details = _details(
        "sympy.integrate", verification=verification, definite=bounds is not None
    )
    if bounds is None and not unresolved:
        residual = sp.simplify(sp.diff(result, variable) - expr)
        details.update(
            verification="verified" if residual == 0 else "unverified",
            residual=sp.sstr(residual),
        )
    if unresolved:
        warnings.append(
            "Se conserva una Integral sin evaluar; el cálculo no está resuelto por completo."
        )
    status = "unresolved" if unresolved else "conditional" if branches else "evaluated"
    if status == "evaluated" and details["verification"] == "unverified":
        status = "unverified"
    return OperationOutcome(result, status, tuple(conditions), tuple(warnings), details)


def _equations(equations):
    items = (
        list(equations)
        if isinstance(equations, (list, tuple, sp.Tuple))
        else [equations]
    )
    if not items:
        raise ValueError("Se requiere al menos una ecuación.")
    residuals = []
    for equation in items:
        if isinstance(equation, sp.Equality):
            residuals.append(equation.lhs - equation.rhs)
        elif isinstance(equation, sp.Expr):
            residuals.append(equation)
        else:
            raise ValueError(  # noqa: TRY004 - uniform backend validation contract
                "Solve requiere ecuaciones de igualdad o expresiones igualadas a cero."
            )
    if any(residual.has(sp.nan, sp.zoo, sp.oo, -sp.oo) for residual in residuals):
        raise ValueError("La ecuación contiene un valor indefinido o no finito.")
    return residuals


def _domain(domain):
    if domain == "Complexes" or domain is sp.S.Complexes:
        return sp.S.Complexes
    if domain == "Reals" or domain is sp.S.Reals:
        return sp.S.Reals
    raise ValueError("El dominio admitido es Reals o Complexes.")


def _conditional_system(residuals, variables, domain, method):
    symbol = variables[0] if len(variables) == 1 else sp.Tuple(*variables)
    base = (
        domain if len(variables) == 1 else sp.ProductSet(*([domain] * len(variables)))
    )
    result = sp.ConditionSet(
        symbol, sp.And(*(sp.Eq(item, 0) for item in residuals)), base
    )
    return OperationOutcome(
        result,
        "unresolved",
        warnings=(
            "El rango o grado depende de parámetros; se conserva el conjunto condicionado sin omitir casos degenerados.",
        ),
        details=_details(
            "symbolic_condition_set", solver=method, verification="not_checked"
        ),
    )


def solve_equations(equations, variables, domain="Complexes"):
    """Use scalar solveset or linear systems, preserving symbolic solution sets."""
    residuals = _equations(equations)
    variables = (
        list(variables)
        if isinstance(variables, (list, tuple, sp.Tuple))
        else [variables]
    )
    if (
        not variables
        or any(not isinstance(item, sp.Symbol) for item in variables)
        or len(set(variables)) != len(variables)
    ):
        raise ValueError("Las variables deben ser símbolos distintos.")
    domain = _domain(domain)
    system = len(residuals) > 1 or len(variables) > 1
    method = "sympy.linsolve" if system else "sympy.solveset"
    if not system:
        expression, variable = residuals[0], variables[0]
        if expression.is_polynomial(variable) and expression != 0:
            leading = sp.Poly(expression, variable).LC()
            if leading.free_symbols and leading.is_zero is None:
                from .symbolic_systems import solve_parameter_branches
                return solve_parameter_branches(expression, variable, domain)
        result = sp.solveset(expression, variable, domain=domain)
    else:
        try:
            matrix, vector = sp.linear_eq_to_matrix(residuals, variables)
        except NonlinearError:
            from .symbolic_systems import solve_polynomial_system
            return solve_polynomial_system(equations, variables, domain)
        if matrix.free_symbols and not (
            matrix.rows == matrix.cols and matrix.det().is_zero is False
        ):
            return _conditional_system(residuals, variables, domain, method)
        result = sp.linsolve((matrix, vector), variables)
    if result is sp.S.EmptySet:
        return OperationOutcome(
            result, "no_solution", details=_details(method, verification="empty_set")
        )
    warnings, verification = [], "not_checked"
    if isinstance(result, sp.FiniteSet):
        verified = True
        for candidate in result:
            values = tuple(candidate) if system else (candidate,)
            substitution = dict(zip(variables, values))
            for residual in residuals:
                check = sp.simplify(residual.subs(substitution, simultaneous=True))
                if check != 0:
                    verified = False
            if system and any(value.free_symbols & set(variables) for value in values):
                warnings.append(
                    "La tupla contiene parámetros libres; no representa un único punto."
                )
        verification = "verified" if verified else "unverified"
        if not verified:
            warnings.append(
                "No se pudo verificar por sustitución cada candidato en todas las ecuaciones."
            )
    if system and domain is sp.S.Reals:
        result = sp.Intersection(result, sp.ProductSet(*([domain] * len(variables))))
    status = "unresolved" if result.has(sp.ConditionSet) else "evaluated"
    if result is sp.S.EmptySet:
        status = "no_solution"
    if status == "unresolved":
        warnings.append(
            "Se conserva un conjunto condicionado; Solve no ha resuelto todas las condiciones."
        )
    details = _details(method, verification=verification, domain=sp.sstr(domain))
    return OperationOutcome(
        result, status, warnings=tuple(dict.fromkeys(warnings)), details=details
    )


def _initial_condition(key, dependent, variable, order):
    derivative_order = 0
    if (
        isinstance(key, AppliedUndef)
        and key.func == dependent.func
        and len(key.args) == 1
    ):
        point = key.args[0]
    elif (
        isinstance(key, sp.Subs)
        and key.variables == (variable,)
        and len(key.point) == 1
    ):
        derivative = key.expr
        if not isinstance(derivative, sp.Derivative) or derivative.expr != dependent:
            raise ValueError(
                "La condición derivada debe referirse a la misma función dependiente."
            )
        if any(item != variable for item in derivative.variables):
            raise ValueError("La condición no puede contener derivadas parciales.")
        derivative_order, point = len(derivative.variables), key.point[0]
    else:
        raise ValueError(
            "La condición debe tener forma y(x0)=valor o derivada evaluada en x0."
        )
    if derivative_order >= order or point.has(variable) or point.is_finite is False:
        raise ValueError(
            "El punto debe ser finito e independiente; el orden inicial debe ser menor que el de la EDO."
        )
    return point, derivative_order


def solve_ode(equations, dependent, variable):
    """Solve one ODE of order 1 or 2; optional equalities provide initial data."""
    variable = _symbol(variable)
    if not isinstance(dependent, AppliedUndef) or dependent.args != (variable,):
        raise ValueError("DSolve requiere una función dependiente ordinaria y(x).")
    items = (
        list(equations)
        if isinstance(equations, (list, tuple, sp.Tuple))
        else [equations]
    )
    if not items or any(not isinstance(item, sp.Equality) for item in items):
        raise ValueError("DSolve requiere una igualdad o una lista de igualdades.")
    ordinary = [
        item for item in items if item.has(sp.Derivative) and not item.has(sp.Subs)
    ]
    if len(ordinary) != 1:
        raise ValueError(
            "DSolve admite una sola EDO junto con condiciones iniciales opcionales."
        )
    equation = ordinary[0]
    if equation.atoms(AppliedUndef) != {dependent}:
        raise ValueError("La EDO debe contener una sola función dependiente y(x).")
    derivatives = equation.atoms(sp.Derivative)
    if any(
        item.expr != dependent or any(arg != variable for arg in item.variables)
        for item in derivatives
    ):
        raise ValueError(
            "No se admiten derivadas parciales ni derivadas de otras funciones."
        )
    order = max(len(item.variables) for item in derivatives)
    if order not in (1, 2):
        raise ValueError("DSolve admite por ahora órdenes 1 y 2.")
    ics, initial_checks = {}, []
    for condition in items:
        if condition is equation:
            continue
        key, value = condition.lhs, condition.rhs
        point, derivative_order = _initial_condition(key, dependent, variable, order)
        _expression(value)
        if value.has(variable, AppliedUndef, sp.Derivative, sp.Subs):
            raise ValueError(
                "El valor inicial debe ser independiente de la variable y de funciones desconocidas."
            )
        if key in ics and sp.simplify(ics[key] - value) != 0:
            raise ValueError(
                "Las condiciones iniciales para el mismo dato son incompatibles."
            )
        ics[key] = value
        initial_checks.append((point, derivative_order, value))
    try:
        result = sp.dsolve(equation, dependent, ics=ics or None)
    except NotImplementedError:
        return OperationOutcome(
            equation,
            "unresolved",
            warnings=("SymPy no resolvió esta EDO en el alcance disponible.",),
            details=_details("sympy.dsolve", verification="not_checked", order=order),
        )
    except ValueError as error:
        raise ValueError(
            f"La EDO o sus condiciones iniciales no pudieron resolverse: {error}"
        ) from error
    solutions = list(result) if isinstance(result, (list, tuple)) else [result]
    if not solutions or any(not isinstance(item, sp.Equality) for item in solutions):
        raise ValueError("El solucionador no devolvió una igualdad de solución.")
    warnings = [
        "La sustitución verifica la familia devuelta; no prueba completitud, existencia/unicidad ni dominio global."
    ]
    residuals, initial_residuals, initial_equation_values, verified = [], [], [], True
    initial_defined = True
    for solution in solutions:
        try:
            valid, residual = sp.checkodesol(equation, solution, func=dependent)
            residuals.append(sp.sstr(residual))
            verified = verified and valid is True
        except (NotImplementedError, ValueError, TypeError):
            residuals.append("not_checked")
            verified = False
        expression = (
            solution.rhs
            if solution.lhs == dependent
            else solution.lhs
            if solution.rhs == dependent
            else None
        )
        for point, derivative_order, expected in initial_checks:
            if expression is None:
                initial_residuals.append("not_checked")
                verified = False
                initial_defined = False
            else:
                residual = sp.simplify(
                    sp.diff(expression, variable, derivative_order).subs(
                        variable, point
                    )
                    - expected
                )
                initial_residuals.append(sp.sstr(residual))
                verified = verified and residual == 0
                # A zero simplified residual can hide two undefined sides at an IC.
                sides = [
                    side.subs(dependent, expression).doit().subs(variable, point)
                    for side in (equation.lhs, equation.rhs)
                ]
                initial_equation_values.append([sp.sstr(side) for side in sides])
                finite = all(side.is_finite is True for side in sides)
                initial_defined = initial_defined and finite
                verified = verified and finite
    value = solutions[0] if len(solutions) == 1 else sp.Tuple(*solutions)
    unresolved = value.has(sp.Integral, sp.Derivative, sp.Order)
    status = "unresolved" if unresolved else "verified" if verified else "unverified"
    if value.has(sp.Order):
        warnings.append(
            "Se conserva una serie truncada; no se presenta como solución exacta completa."
        )
    if status != "verified":
        warnings.append(
            "La solución no está completamente evaluada o no se ha verificado junto con todos sus datos iniciales."
        )
    if not initial_defined:
        warnings.append(
            "La EDO no quedó definida y finita en todos los puntos de los datos iniciales."
        )
    return OperationOutcome(
        value,
        status,
        warnings=tuple(warnings),
        details=_details(
            "sympy.dsolve",
            verification="verified" if verified else "unverified",
            order=order,
            ode_residuals=residuals,
            initial_residuals=initial_residuals,
            initial_conditions=len(ics),
            initial_equation_values=initial_equation_values,
            initial_defined=initial_defined,
        ),
    )
