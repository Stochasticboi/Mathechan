"""Differential operators on regular cylindrical and spherical charts.

Vector and tensor components use the local orthonormal basis. Jacobian in
Components mode instead means the ordinary derivative of component functions.
"""

import sympy as sp

from .calculus import OperationOutcome
from .differential_ops import _budget, _outcome, _scalar, _variables, _vector


def _chart(variables, chart):
    variables = _variables(variables)
    if len(variables) != 3:
        raise ValueError("Las cartas cilíndricas y esféricas requieren tres coordenadas.")
    if chart == "Cylindrical":
        factors = (sp.S.One, variables[0], sp.S.One)
    elif chart == "Spherical":
        factors = (sp.S.One, variables[0], variables[0]*sp.sin(variables[1]))
    else:
        raise ValueError("La carta debe ser Cylindrical o Spherical.")
    return variables, factors


def chart_conditions(variables, chart):
    """Return the regular real chart requirements without assuming periodic cuts."""
    variables, _ = _chart(variables, chart)
    if any(variable.is_real is False for variable in variables):
        raise ValueError("Las coordenadas de la carta deben ser reales.")
    requirements = [sp.Contains(variable, sp.S.Reals) for variable in variables]
    requirements.append(sp.Gt(variables[0], 0))
    if chart == "Spherical":
        requirements.extend((sp.Gt(variables[1], 0), sp.Lt(variables[1], sp.pi)))
    if any(condition is sp.S.false for condition in requirements):
        raise ValueError("Los supuestos de las coordenadas contradicen la carta regular.")
    return tuple(condition for condition in requirements if condition is not sp.S.true)


def _refinement(variables, chart):
    assumptions = [sp.Q.real(variable) for variable in variables]
    assumptions.append(sp.Q.positive(variables[0]))
    if chart == "Spherical":
        assumptions.append(sp.Q.positive(sp.sin(variables[1])))
    return sp.And(*assumptions)


def _connection(variables, factors):
    """Levi-Civita connection for g_ij = delta_ij h_i**2."""
    metric = tuple(factor**2 for factor in factors)
    return {
        (k, i, j): sp.simplify(
            ((sp.diff(metric[k], variables[i]) if j == k else 0)
             + (sp.diff(metric[k], variables[j]) if i == k else 0)
             - (sp.diff(metric[i], variables[k]) if i == j else 0))
            / (2*metric[k]))
        for k in range(3) for i in range(3) for j in range(3)
    }


def _vector_gradient(expressions, variables, factors, connection):
    # V^i = A_i/h_i; each derivative direction is e_j = (1/h_j) d/dq_j.
    contravariant = tuple(expressions[i]/factors[i] for i in range(3))
    return sp.ImmutableMatrix(3, 3, lambda i, j:
        factors[i]/factors[j] * (
            sp.diff(contravariant[i], variables[j])
            + sum(connection[i, j, k]*contravariant[k] for k in range(3))))


def coordinate_operator(operation, expr, variables, chart, mode="Components"):
    """Evaluate bounded differential operators with explicit chart conditions."""
    variables, factors = _chart(variables, chart)
    requirements = chart_conditions(variables, chart)
    if operation not in {"Grad", "Div", "Curl", "Hessian", "Jacobian"}:
        raise ValueError("Operador diferencial vectorial desconocido.")
    if mode not in {"Components", "Orthonormal"}:
        raise ValueError("El modo del jacobiano debe ser Components u Orthonormal.")
    if operation != "Jacobian" and mode != "Components":
        raise ValueError("El modo adicional se admite únicamente en Jacobian.")
    vector_input = isinstance(expr, (sp.MatrixBase, list, tuple, sp.Tuple))
    if operation == "Hessian" and vector_input:
        raise ValueError("Hessian requiere una expresión escalar.")
    expressions = _vector(expr) if vector_input else (_scalar(expr),)
    if operation in {"Div", "Curl", "Jacobian"} and not vector_input:
        raise ValueError("El operador requiere un campo vectorial.")
    if ((operation in {"Div", "Curl", "Grad"} and vector_input)
            or (operation == "Jacobian" and mode == "Orthonormal")):
        if len(expressions) != 3:
            raise ValueError("El campo físico debe tener tres componentes ortonormales.")
    _budget(expressions, variables)
    assumptions = _refinement(variables, chart)
    refined = tuple(sp.refine(item, assumptions) for item in expressions)
    if operation == "Grad" and not vector_input:
        value = sp.ImmutableMatrix([sp.diff(refined[0], q)/h
                                    for q, h in zip(variables, factors)])
    elif operation == "Jacobian" and mode == "Components":
        value = sp.ImmutableMatrix(refined).jacobian(variables).as_immutable()
    elif operation == "Div":
        volume = sp.prod(factors)
        value = sum(sp.diff(volume*refined[i]/factors[i], variables[i])
                    for i in range(3))/volume
    elif operation == "Curl":
        value = sp.ImmutableMatrix([
            (sp.diff(factors[k]*refined[k], variables[j])
             - sp.diff(factors[j]*refined[j], variables[k]))/(factors[j]*factors[k])
            for j, k in ((1, 2), (2, 0), (0, 1))])
    else:
        connection = _connection(variables, factors)
        if operation == "Hessian":
            scalar = refined[0]
            value = sp.ImmutableMatrix(3, 3, lambda i, j:
                (sp.diff(scalar, variables[i], variables[j])
                 - sum(connection[k, i, j]*sp.diff(scalar, variables[k])
                       for k in range(3)))/(factors[i]*factors[j]))
        else:
            value = _vector_gradient(refined, variables, factors, connection)
    # Check growth before and after simplification; neither is a global timeout.
    _outcome(value, operation, expressions, variables)
    if isinstance(value, sp.MatrixBase):
        value = value.applyfunc(lambda item: sp.refine(sp.trigsimp(item), assumptions))
    else:
        value = sp.refine(sp.trigsimp(value), assumptions)
    outcome = _outcome(value, operation, expressions, variables,
                       coordinates=chart,
                       basis=("component_functions_by_coordinate" if operation == "Jacobian"
                              and mode == "Components" else "orthonormal"),
                       matrix_axes=(
                           {"rows": "component_functions", "columns": "chart_coordinates"}
                           if operation == "Jacobian" and mode == "Components"
                           else {"rows": "orthonormal_components", "columns": "orthonormal_directions"}
                           if isinstance(value, sp.MatrixBase) and value.cols == 3
                           else None),
                       scale_factors=[sp.sstr(item) for item in factors],
                       chart_convention=(
                           "(radius, polar_angle_from_positive_z, azimuth); radius > 0; 0 < polar_angle < Pi"
                           if chart == "Spherical" else
                           "(radius, azimuth, axial_coordinate); radius > 0"),
                       azimuth="local_real_coordinate_without_periodic_cut",
                       chart_requirements=[sp.sstr(item) for item in requirements],
                       jacobian_mode=mode if operation == "Jacobian" else None)
    status = "conditional" if requirements and outcome.status != "unresolved" else outcome.status
    return OperationOutcome(outcome.value, status,
                            conditions=tuple(sp.sstr(item) for item in requirements),
                            warnings=outcome.warnings, details=outcome.details)
