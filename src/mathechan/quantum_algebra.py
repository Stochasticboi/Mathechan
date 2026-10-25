"""Small complex-vector operations with explicit nonzero-norm requirements."""

import sympy as sp

from .assumptions import combine_assumptions, predicates
from .calculus import OperationOutcome
from .linear_algebra import _array, _scalar

QUANTUM_CORE_CALLS = frozenset({"Conj", "Re", "Im", "Adj", "Inner", "Norm", "Unit", "Dyad", "Proj", "Kron", "Ortho"})


def _entries(value):
    if isinstance(value, sp.MatrixBase):
        return list(value)
    if isinstance(value, (tuple, list, sp.Tuple)):
        return [entry for child in value for entry in _entries(child)]
    return [_scalar(value)]


def _budget(arguments):
    entries = [entry for value in arguments for entry in _entries(value)]
    if len(entries) > 256 or sum(int(sp.count_ops(entry)) for entry in entries) > 256:
        raise ValueError("El cálculo complejo admite 256 entradas y 256 operaciones de entrada.")
    symbols = set().union(*(entry.free_symbols for entry in entries)) if entries else set()
    if len(symbols) > 8:
        raise ValueError("El cálculo complejo admite hasta ocho símbolos.")
    if any(entry.is_finite is False for entry in entries):
        raise ValueError("Las entradas deben ser finitas.")
    return entries


def _ket(value):
    matrix, flat = _array(value)
    if matrix.cols != 1:
        raise ValueError("Se requiere un vector plano o una matriz columna; no un bra ni una matriz general.")
    return matrix, flat


def _inner(left, right):
    if left.rows != right.rows:
        raise ValueError("Los vectores deben tener la misma dimensión.")
    return sp.simplify(sum((sp.conjugate(a)*b for a,b in zip(left,right)), sp.S.Zero))


def _norm_squared(vector):
    return sp.simplify(sum((sp.Abs(item)**2 for item in vector), sp.S.Zero))


def _positive(value, assumptions):
    condition = sp.Gt(value, 0)
    constants = {}
    for equality in sp.And.make_args(assumptions):
        if isinstance(equality, sp.Equality):
            if isinstance(equality.lhs, sp.Symbol) and not equality.rhs.free_symbols:
                constants[equality.lhs] = equality.rhs
            elif isinstance(equality.rhs, sp.Symbol) and not equality.lhs.free_symbols:
                constants[equality.rhs] = equality.lhs
    sampled = sp.simplify(condition.subs(constants, simultaneous=True))
    try:
        truth = sp.ask(predicates(sampled), predicates(assumptions))
    except (ValueError, TypeError, NotImplementedError):
        truth = None
    if sampled is sp.false or truth is False:
        raise ValueError("Se requiere norma estrictamente positiva; un vector nulo o dependiente no se normaliza.")
    combine_assumptions(assumptions, condition)
    if sampled is sp.true or truth is True:
        return ()
    return (condition,)


def _result(value, operation, requirements=(), warnings=(), **details):
    entries = _entries(value)
    if len(entries) > 64 or sum(int(sp.count_ops(entry)) for entry in entries) > 4096:
        raise ValueError("El resultado complejo excede 64 entradas o 4096 operaciones.")
    if any(entry.has(sp.zoo, sp.nan, sp.oo, -sp.oo) or entry.is_finite is False for entry in entries):
        raise ValueError("El resultado contiene valores no finitos.")
    if isinstance(value, sp.MatrixBase):
        value = value.as_immutable()
    requirements = tuple(dict.fromkeys(requirements))
    return OperationOutcome(value, "conditional" if requirements else "evaluated",
                            conditions=tuple(map(sp.sstr,requirements)), warnings=tuple(warnings),
                            details={"operation":operation, "method":"complex_dense_algebra",
                                     "sympy_version":sp.__version__, "domain_analysis":"partial",
                                     "precision_certified":False, **details}), requirements


def quantum_operation(name, args, assumptions=sp.true):
    """Return (outcome, executable requirements), without parsing source text.

    Inner is antilinear in its first argument. List vectors are kets, while
    explicit matrices retain their orientation. Kron orders factors left to
    right, with the first factor the most significant subsystem.
    """
    arities = {"Conj":1,"Re":1,"Im":1,"Adj":1,"Inner":2,"Norm":1,"Unit":1,"Dyad":2,"Proj":1,"Ortho":1}
    if name not in QUANTUM_CORE_CALLS or (name == "Kron" and not 2 <= len(args) <= 8) or (
            name != "Kron" and len(args) != arities[name]):
        raise ValueError("Operación compleja desconocida o número de argumentos incorrecto.")
    entries = _budget(args)
    warnings = []
    floats = set().union(*(entry.atoms(sp.Float) for entry in entries)) if entries else set()
    if floats:
        warnings.append("Entradas aproximadas: no se usa una tolerancia para declarar normas nulas ni se certifica precisión.")
    requirements = []
    if name in {"Conj","Re","Im"}:
        function = {"Conj":sp.conjugate,"Re":sp.re,"Im":sp.im}[name]
        argument = args[0]
        if isinstance(argument, (sp.MatrixBase, tuple, list, sp.Tuple)):
            matrix, flat = _array(argument)
            value = matrix.applyfunc(function)
            value = sp.Tuple(*value) if flat else value
        else:
            value = function(_scalar(argument))
    elif name == "Adj":
        matrix, _ = _array(args[0])
        value = matrix.H
    elif name == "Kron":
        arrays = [_array(argument) for argument in args]
        rows = sp.prod(matrix.rows for matrix,_ in arrays)
        cols = sp.prod(matrix.cols for matrix,_ in arrays)
        if rows > 8 or cols > 8 or rows*cols > 64:
            raise ValueError("Kron excede ocho filas/columnas o 64 entradas; no se construyó el producto.")
        value = sp.kronecker_product(*(matrix for matrix,_ in arrays))
        if all(flat for _,flat in arrays):
            value = sp.Tuple(*value)
        return _result(value,name,warnings=warnings,subsystem_order="left_to_right_most_significant_first",
                       factor_shapes=[list(matrix.shape) for matrix,_ in arrays])
    elif name == "Ortho":
        raw = args[0]
        if not isinstance(raw, (tuple,list,sp.Tuple)) or not 1 <= len(raw) <= 8:
            raise ValueError("Ortho requiere entre uno y ocho vectores, no una matriz implícita de columnas.")
        vectors = [_ket(item)[0] for item in raw]
        if len({vector.rows for vector in vectors}) != 1 or len(vectors) > vectors[0].rows:
            raise ValueError("Ortho requiere vectores de igual dimensión y no más vectores que dimensiones.")
        precision = min((entry._prec for entry in floats),default=None)
        digits = max(2,int(precision*0.30103)) if precision else None
        if floats:
            if any(abs(entry._mpf_[2]) > 10000 or entry._prec > 4096 for entry in floats):
                raise ValueError("Los datos aproximados exceden el presupuesto de precisión o exponente.")
            mapping = {entry:sp.Rational(entry) for entry in floats}
            vectors = [vector.xreplace(mapping) for vector in vectors]
            warnings.append("Ortho usa los racionales binarios almacenados antes de Gram–Schmidt y evalúa al final; la incertidumbre de entrada no se modela.")
        basis = []
        scales = []
        for vector in vectors:
            residual = vector
            for previous in basis:
                residual = (residual-previous*_inner(previous,residual)).applyfunc(sp.simplify)
            squared = _norm_squared(residual)
            original_squared = _norm_squared(vector)
            if floats and not squared.free_symbols and original_squared.is_zero is not True:
                ratio = (squared/original_squared).evalf(digits)
                scales.append(sp.sstr(ratio))
                if ratio.is_positive is True and ratio < sp.Rational(1,10**12):
                    warnings.append("La base de entrada es casi dependiente; la incertidumbre de los datos puede cambiar fuertemente los vectores ortonormales.")
            requirements.extend(_positive(squared,sp.And(assumptions,*requirements)))
            normalized = residual.applyfunc(lambda item:sp.simplify(item/sp.sqrt(squared)))
            basis.append(normalized)
        value = sp.Tuple(*(sp.Tuple(*(entry.evalf(digits) if digits else entry for entry in vector))
                           for vector in basis))
        return _result(value,name,requirements,warnings,algorithm="ordered_hermitian_gram_schmidt",
                       output_convention="list_of_orthonormal_kets",conjugation="first_argument",
                       input_precision_bits=precision,evaluation_digits=digits,
                       squared_residual_to_input_norm_ratios=scales)
    else:
        left, flat = _ket(args[0])
        if name in {"Inner","Dyad"}:
            right, _ = _ket(args[1])
            value = _inner(left,right) if name == "Inner" else left*right.H
        else:
            squared = _norm_squared(left)
            if name == "Norm":
                value = sp.sqrt(squared)
            else:
                requirements.extend(_positive(squared,assumptions))
                if name == "Proj":
                    value = sp.ImmutableMatrix(left.rows,left.rows,lambda i,j:sp.simplify(
                        (sp.Abs(left[i])**2 if i == j else left[i]*sp.conjugate(left[j]))/squared))
                else:
                    value = left.applyfunc(lambda item:sp.simplify(item/sp.sqrt(squared)))
                    value = sp.Tuple(*value) if flat else value
    return _result(value,name,requirements,warnings,conjugation="first_argument" if name == "Inner" else "explicit")
