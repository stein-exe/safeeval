"""Public entry point for safeeval."""

from __future__ import annotations

from ._parser import parse
from ._tokenizer import tokenize


def evaluate(expression: str) -> float:
    """Safely evaluate an arithmetic *expression* and return a float.

    Supported operators: ``+ - * / % **`` plus parentheses and unary
    ``+``/``-``. Precedence and associativity follow Python.

    The function never calls :func:`eval`, :func:`exec`,
    :func:`ast.literal_eval` or any third-party parser — the only inputs
    accepted are numeric literals and the listed operators.

    Parameters
    ----------
    expression : str
        The arithmetic expression to evaluate.

    Returns
    -------
    float
        The computed value.

    Raises
    ------
    SyntaxError
        If *expression* is malformed.
    ZeroDivisionError
        If the expression performs division or modulo by zero.
    ValueError
        If the expression produces a non-real result (e.g. a negative
        base raised to a fractional power).
    """
    tokens = tokenize(expression)
    return parse(tokens)
