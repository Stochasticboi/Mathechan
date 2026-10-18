"""Cuaderno JSON v0.1: abrir y guardar nunca evalúa las celdas."""

from copy import deepcopy
import json
from pathlib import Path
from uuid import uuid4

import sympy as sp

from . import __version__


class NotebookError(ValueError):
    """Un cuaderno incumple el esquema v0.1."""


MAX_BYTES = 2_000_000


def new_notebook():
    """Crea un documento vacío con versiones explícitas."""
    return {
        "format": "mathechan-notebook",
        "version": "0.1",
        "versions": {"kernel": __version__, "sympy": sp.__version__},
        "cells": [],
    }


def new_cell(source, kind="code"):
    """Crea una celda; results solo admite texto inerte en esta versión."""
    cell = {"id": str(uuid4()), "kind": kind, "source": source, "results": []}
    document = new_notebook()
    document["cells"].append(cell)
    validate_notebook(document)
    return cell


def exact_keys(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise NotebookError(f"Campos no válidos en {label}.")


def require_utf8(value, label):
    """Rechaza sustitutos Unicode que no representan texto UTF-8 válido."""
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise NotebookError(f"{label} contiene un sustituto Unicode no válido en UTF-8.") from error


def validate_notebook(document):
    """Valida forma, versiones, identificadores y contenido sin ejecutar código."""
    exact_keys(document, ("format", "version", "versions", "cells"), "documento")
    if document["format"] != "mathechan-notebook" or document["version"] != "0.1":
        raise NotebookError("Formato o versión no admitidos.")
    exact_keys(document["versions"], ("kernel", "sympy"), "versions")
    if any(not isinstance(value, str) or not value or len(value) > 100 for value in document["versions"].values()):
        raise NotebookError("Las versiones deben ser cadenas breves no vacías.")
    for name, value in document["versions"].items():
        require_utf8(value, f"versions.{name}")
    cells = document["cells"]
    if not isinstance(cells, list) or len(cells) > 1000:
        raise NotebookError("cells debe ser una lista de hasta 1000 celdas.")
    ids = set()
    for cell in cells:
        exact_keys(cell, ("id", "kind", "source", "results"), "celda")
        if not isinstance(cell["id"], str) or not cell["id"] or len(cell["id"]) > 100 or cell["id"] in ids:
            raise NotebookError("Cada celda requiere un id único y no vacío de hasta 100 caracteres.")
        require_utf8(cell["id"], "id")
        ids.add(cell["id"])
        if cell["kind"] not in ("code", "markdown"):
            raise NotebookError("kind debe ser code o markdown.")
        if not isinstance(cell["source"], str) or len(cell["source"]) > 100_000:
            raise NotebookError("source debe ser texto de hasta 100000 caracteres.")
        require_utf8(cell["source"], "source")
        if not isinstance(cell["results"], list) or len(cell["results"]) > 100:
            raise NotebookError("results debe ser una lista de hasta 100 resultados.")
        for result in cell["results"]:
            exact_keys(result, ("kind", "text"), "resultado")
            if result["kind"] != "text" or not isinstance(result["text"], str) or len(result["text"]) > 100_000:
                raise NotebookError("Solo se admiten resultados de texto de hasta 100000 caracteres.")
            require_utf8(result["text"], "results.text")
    return deepcopy(document)


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise NotebookError(f"Campo JSON duplicado: {key}.")
        result[key] = value
    return result


def invalid_constant(value):
    raise NotebookError(f"Constante JSON no admitida: {value}.")


def load_notebook(path):
    """Lee hasta el límite de bytes UTF-8; source y results permanecen inertes."""
    with Path(path).open("rb") as stream:
        content = stream.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise NotebookError("El cuaderno excede 2 MB.")
    try:
        document = json.loads(content.decode("utf-8"), object_pairs_hook=no_duplicate_keys,
                              parse_constant=invalid_constant)
        return validate_notebook(document)
    except NotebookError:
        raise
    except (ValueError, UnicodeError, RecursionError) as error:
        raise NotebookError(f"JSON no válido: {error}") from error


def save_notebook(document, path):
    """Guarda UTF-8 con LF, contando exactamente los bytes que se escriben."""
    validated = validate_notebook(document)
    content = (json.dumps(validated, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if len(content) > MAX_BYTES:
        raise NotebookError("El cuaderno excede 2 MB.")
    Path(path).write_bytes(content)
