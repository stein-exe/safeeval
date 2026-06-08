"""safeeval — a small, dependency-free arithmetic expression evaluator.

Public API
----------
- :func:`evaluate` — parse and evaluate a string expression to a float.

The implementation is split into three internal modules:

- :mod:`safeeval._tokenizer` — character scanner
- :mod:`safeeval._parser` — Pratt parser
- :mod:`safeeval._evaluator` — public entry point

The internals are prefixed with an underscore and should not be
considered part of the stable API.
"""

from ._evaluator import evaluate

__all__ = ["evaluate"]
__version__ = "0.1.0"
