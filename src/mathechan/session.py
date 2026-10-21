"""Bounded immediate numeric definitions for one local evaluation session."""

from dataclasses import replace

import sympy as sp

from .kernel import FUNCTIONS, MathechanError, Parser, _evaluate_node
from .language_ops import SCIENTIFIC_CALLS

MAX_DEFINITIONS = 64
PROTECTED_NAMES = (
    frozenset(FUNCTIONS)
    | SCIENTIFIC_CALLS
    | {
        "Pi",
        "E",
        "Infinity",
        "Plot",
        "Reals",
        "Complexes",
    }
)
ASSIGNABLE_STATUSES = frozenset({"evaluated", "approximate", "verified", "solved"})


class Session:
    """Keep at most 64 finite numeric snapshots; no symbolic or delayed definitions."""

    def __init__(self):
        self._definitions = {}

    def evaluate(self, source):
        """Evaluate one expression or commit one validated root assignment atomically."""
        node = Parser(source, allow_assignment=True).parse()
        name = node.value if node.kind == "assignment" else None
        if name is not None:
            if name in PROTECTED_NAMES:
                raise MathechanError(
                    f"El nombre {name} está protegido y no admite asignación."
                )
            if (
                name not in self._definitions
                and len(self._definitions) >= MAX_DEFINITIONS
            ):
                raise MathechanError(
                    "La sesión admite como máximo 64 variables numéricas."
                )
            node = node.children[0]
        result, value = _evaluate_node(node, source, dict(self._definitions))
        if name is not None:
            if (
                not isinstance(value, sp.Expr)
                or value.is_commutative is not True
                or value.is_number is not True
                or value.free_symbols
                or value.is_finite is not True
                or result.conditions
                or result.status not in ASSIGNABLE_STATUSES
            ):
                raise MathechanError(
                    "La asignación requiere un escalar numérico finito e incondicional, "
                    "sin símbolos libres ni resultados pendientes de verificar."
                )
            result = replace(
                result, details={**result.details, "assignment": {"name": name}}
            )
            self._definitions[name] = value
        elif (
            result.input is not None
            and value is not None
            and any(symbol.name in self._definitions for symbol in value.free_symbols)
        ):
            warning = (
                "La entrada reutilizable se verifica sin definiciones de sesión; "
                "volver a evaluarla aquí puede sustituir nombres definidos."
            )
            result = replace(
                result, warnings=tuple(dict.fromkeys((*result.warnings, warning)))
            )
        return result
