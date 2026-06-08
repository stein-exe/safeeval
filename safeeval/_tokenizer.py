"""Tokenizer for safeeval.

A small character-by-character scanner that converts a source string into
a flat list of tokens. The grammar is intentionally tiny:

    number  ::=  digit+ ( "." digit+ )? | "." digit+
    op      ::=  "+" | "-" | "*" | "/" | "%" | "**"
    paren   ::=  "(" | ")"

The tokenizer does not interpret operators or perform any evaluation;
it only produces a token stream the parser can walk.

Token representation
--------------------
A token is a 3-element ``tuple`` ``(kind, value, position)``:

* ``kind``     — one of ``"NUMBER"``, ``"OP"``, ``"LPAREN"``, ``"RPAREN"``
* ``value``    — the raw text (``"+"``, ``"**"``, ``"3.14"`` …)
* ``position`` — the zero-based character offset (for error messages)

We use a plain tuple rather than a dataclass because the tokenizer is
on the hot path; the dataclass constructor adds measurable overhead.
Tests and external code should use the :data:`Token` alias and access
fields by ``[0]`` / ``[1]`` / ``[2]`` or by the constants below.
"""

from __future__ import annotations

from typing import List, Tuple

#: A token: ``(kind, value, position)``. See module docstring.
Token = Tuple[str, str, int]

# Index constants for unpacking tokens positionally.
_KIND = 0
_VALUE = 1
_POSITION = 2


# Operator characters that can be valid start of a binary operator. The
# parser decides which operator is actually present; "**" is detected
# from a "**" pair, "++" is never produced.
_BINARY_OP_CHARS = frozenset("+-*/%")

# Lookup tables for the hot inner loop. Using ``in frozenset`` is
# noticeably faster than calling ``str.isspace()`` / ``str.isdigit()``
# because the latter methods also handle Unicode categories we don't
# care about here.
_WHITESPACE = frozenset(" \t\n\r\f\v")
_DIGITS = frozenset("0123456789")


def tokenize(source: str) -> List[Token]:
    """Tokenize *source* into a list of :class:`Token`.

    Parameters
    ----------
    source : str
        The arithmetic expression to tokenize.

    Returns
    -------
    list[Token]
        The token stream. An empty source yields an empty list.

    Raises
    ------
    SyntaxError
        If an unexpected character is encountered or a number literal is
        malformed (e.g. ``"1."`` with no trailing digits, or ``".."``).
    """
    tokens: List[Token] = []
    i = 0
    n = len(source)

    while i < n:
        c = source[i]

        # Whitespace is silently skipped.
        if c in _WHITESPACE:
            i += 1
            continue

        # Numbers: either a sequence starting with a digit, or a leading
        # '.' followed by digits. A trailing dot without digits is a
        # syntax error caught below by the explicit check after the loop.
        if c in _DIGITS or (c == "." and i + 1 < n and source[i + 1] in _DIGITS):
            start = i
            i = _consume_number(source, i)
            tokens.append(("NUMBER", source[start:i], start))
            continue

        if c == "(":
            tokens.append(("LPAREN", "(", i))
            i += 1
            continue

        if c == ")":
            tokens.append(("RPAREN", ")", i))
            i += 1
            continue

        # Operators. "**" must be detected before single "*" so we don't
        # split it into two tokens.
        if c in _BINARY_OP_CHARS:
            start = i
            if c == "*" and i + 1 < n and source[i + 1] == "*":
                i += 2
                tokens.append(("OP", "**", start))
            else:
                i += 1
                tokens.append(("OP", c, start))
            continue

        raise SyntaxError(
            f"Unexpected character {c!r} at position {i}"
        )

    return tokens


def _consume_number(source: str, i: int) -> int:
    """Consume a number literal starting at *i* and return the new index.

    Accepts forms like ``42``, ``3.14``, ``.5`` and ``2.0``. A trailing
    ``.`` with no digits afterwards is rejected.
    """
    n = len(source)
    digits = _DIGITS

    if source[i] == ".":
        # Leading dot. The caller guarantees the next char is a digit
        # (otherwise we wouldn't be here), so consume that digit and
        # any further digits. A "lone" "." never reaches this function.
        i += 1
        while i < n and source[i] in digits:
            i += 1
        return i

    # First char is a digit. Consume all digits.
    while i < n and source[i] in digits:
        i += 1

    # Optional fractional part: a '.' followed by at least one digit.
    if i < n and source[i] == ".":
        if i + 1 < n and source[i + 1] in digits:
            i += 1
            while i < n and source[i] in digits:
                i += 1
        else:
            # Trailing dot is a syntax error.
            raise SyntaxError(
                f"Trailing '.' in number literal at position {i}"
            )

    return i
