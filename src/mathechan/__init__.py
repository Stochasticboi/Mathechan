"""Mathechan: prototipo experimental; sin compatibilidad completa con Wolfram."""

__version__ = "0.2.0.dev2"

from .kernel import EvaluationResult, MathechanError, evaluate
from .session import Session

__all__ = ["EvaluationResult", "MathechanError", "Session", "__version__", "evaluate"]
