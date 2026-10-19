"""Mathechan: prototipo experimental; sin compatibilidad completa con Wolfram."""

__version__ = "0.1.1"

from .kernel import EvaluationResult, MathechanError, evaluate

__all__ = ["EvaluationResult", "MathechanError", "evaluate", "__version__"]
