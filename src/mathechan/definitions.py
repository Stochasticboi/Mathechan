"""Immutable mathematical snapshots owned by an evaluation session."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StoredDefinition:
    """A computed expression and the conditions retained before simplification."""

    value: object
    restrictions: tuple = ()
    requirements: tuple = ()
    warnings: tuple = ()
    approximate: bool = False


@dataclass(frozen=True)
class UserFunction:
    """A fixed expression with distinct dummy parameters and retained conditions."""

    parameters: tuple
    body: StoredDefinition
    names: tuple = ()


@dataclass(frozen=True)
class DeferredDefinition:
    """Syntax evaluated only when the definition is explicitly requested."""

    node: object


@dataclass(frozen=True)
class DeferredFunction:
    """Bounded deferred syntax with lexical parameter aliases and optional patterns."""

    parameters: tuple
    names: tuple
    node: object
    patterns: tuple = ()
