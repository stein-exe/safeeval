"""Pratt (top-down operator precedence) parser for safeeval.

The parser walks a flat list of tokens and produces a Python ``float``.
It does not build an intermediate AST: the parse and evaluate steps are
fused, which keeps memory usage low and avoids a second traversal.

Binding powers
--------------
Operator precedence is encoded as ``(left_bp, right_bp)`` pairs.
A higher binding power binds more tightly.

* ``+``, ``-`` (binary):  10 / 11  (left-associative)
* ``*``, ``/``, ``%``:    20 / 21  (left-associative)
* ``**``:                30 / 30  (right-associative)
* Unary ``-``, ``+``:    prefix bp 25

The prefix binding power of 25 (less than 30) ensures that
``-2 ** 2`` parses as ``-(2**2)`` — matching Python's rule that
unary minus binds *looser* than ``**``.

When ``left_bp`` and ``right_bp`` differ by 1, the operator is
left-associative; when they are equal, right-associative.

Tokens are tuples ``(kind, value, position)``; the parser uses
positional access via the ``_KIND`` / ``_VALUE`` / ``_POSITION``
constants for speed.
"""

from __future__ import annotations

from typing import List

from ._tokenizer import Token, _KIND, _VALUE, _POSITION


def _safe_pow(a: float, b: float) -> float:
    """Exponentiation that raises ``ValueError`` instead of returning a
    complex number for non-real results (e.g. ``(-1.0) ** 0.5``)."""
    try:
        result = a ** b
    except OverflowError as exc:
        # 10 ** 1000 etc. — surface as a more meaningful domain error.
        raise OverflowError(
            f"Exponentiation overflow: ({a}) ** ({b})"
        ) from exc
    if isinstance(result, complex):
        raise ValueError(
            f"Expression is not a real number: ({a}) ** ({b}) = {result}"
        )
    return result


_BINARY_OPS: dict = {
    "+": (10, 11, lambda a, b: a + b),
    "-": (10, 11, lambda a, b: a - b),
    "*": (20, 21, lambda a, b: a * b),
    "/": (20, 21, lambda a, b: a / b),
    "%": (20, 21, lambda a, b: a % b),
    "**": (30, 30, _safe_pow),
}

# Prefix binding power for unary operators. 25 < 30 means unary binds
# looser than "**" — see module docstring for the rationale.
_UNARY_PREFIX_BP = 25

_UNARY_OPS = {
    "-": lambda a: -a,
    "+": lambda a: +a,
}


class _Parser:
    """Stateful Pratt parser. One instance per ``parse`` call."""

    __slots__ = ("_tokens", "_pos", "_n")

    def __init__(self, tokens: List[Token]) -> None:
        self._tokens = tokens
        self._pos = 0
        self._n = len(tokens)  # cached to avoid repeated len() calls

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _consume(self) -> Token:
        pos = self._pos
        if pos >= self._n:
            raise SyntaxError("Unexpected end of expression")
        tok = self._tokens[pos]
        self._pos = pos + 1
        return tok

    # ------------------------------------------------------------------
    # Pratt core
    # ------------------------------------------------------------------
    def parse(self) -> float:
        """Parse the entire token stream and return a float value."""
        if self._pos >= self._n:
            raise SyntaxError("Empty expression")

        value = self._parse_expression(min_bp=0)
        if self._pos < self._n:
            tok = self._tokens[self._pos]
            raise SyntaxError(
                f"Unexpected token {tok[_VALUE]!r} at position {tok[_POSITION]}"
            )
        return value

    def _parse_expression(self, min_bp: int) -> float:
        # ----- prefix / atom -----
        tok = self._consume()
        kind = tok[_KIND]
        if kind == "NUMBER":
            # float() on the textual form is faster and preserves the
            # exact decimal as written (e.g. "0.1" -> 0.1).
            value: float = float(tok[_VALUE])
        elif kind == "LPAREN":
            value = self._parse_expression(min_bp=0)
            closing = self._consume()
            if closing[_KIND] != "RPAREN":
                raise SyntaxError(
                    f"Expected ')' at position {closing[_POSITION]}, "
                    f"got {closing[_VALUE]!r}"
                )
        elif kind == "OP":
            fn = _UNARY_OPS.get(tok[_VALUE])
            if fn is None:
                raise SyntaxError(
                    f"Unexpected token {tok[_VALUE]!r} at position {tok[_POSITION]}"
                )
            operand = self._parse_expression(_UNARY_PREFIX_BP)
            value = fn(operand)
        else:
            raise SyntaxError(
                f"Unexpected token {tok[_VALUE]!r} at position {tok[_POSITION]}"
            )

        # ----- infix -----
        # Local aliases for the hot loop. ``tokens`` and ``n`` are
        # invariant for the lifetime of the parser, so we hoist them
        # out and only refresh ``pos`` from ``self._pos`` after the
        # recursive call.
        tokens = self._tokens
        n = self._n
        pos = self._pos
        binary_ops = _BINARY_OPS
        while pos < n:
            tok = tokens[pos]
            if tok[_KIND] != "OP":
                break
            op_info = binary_ops.get(tok[_VALUE])
            if op_info is None:
                raise SyntaxError(
                    f"Unknown operator {tok[_VALUE]!r} at position {tok[_POSITION]}"
                )
            left_bp, right_bp, fn = op_info
            if left_bp < min_bp:
                break
            pos += 1
            self._pos = pos
            rhs = self._parse_expression(right_bp)
            value = fn(value, rhs)
            # The recursive call updated self._pos; mirror it here.
            pos = self._pos

        self._pos = pos
        return value


def parse(tokens: List[Token]) -> float:
    """Parse *tokens* (a list from :func:`safeeval._tokenizer.tokenize`)
    and return the resulting ``float`` value.

    Raises
    ------
    SyntaxError
        For any structural problem (empty stream, unmatched parens,
        trailing operator, etc.).
    ZeroDivisionError
        If division or modulo by zero is requested at parse time.
        Note: the actual evaluation is fused with parsing, so the error
        is raised by this function too.
    """
    return _Parser(tokens).parse()
