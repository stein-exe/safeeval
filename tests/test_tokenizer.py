"""Tests for the tokenizer."""

import pytest

from safeeval._tokenizer import (
    _KIND,
    _POSITION,
    _VALUE,
    tokenize,
)


def T(kind, value, position):
    """Test helper: build a token tuple positionally.

    Equivalent to the old ``Token(kind, value, position)`` dataclass call.
    """
    return (kind, value, position)


# ----------------------------------------------------------------------
# Happy path
# ----------------------------------------------------------------------
class TestNumbers:
    def test_integer(self):
        assert tokenize("42") == [T("NUMBER", "42", 0)]

    def test_float(self):
        assert tokenize("3.14") == [T("NUMBER", "3.14", 0)]

    def test_float_no_leading_digit(self):
        assert tokenize(".5") == [T("NUMBER", ".5", 0)]

    def test_zero(self):
        assert tokenize("0") == [T("NUMBER", "0", 0)]

    def test_long_number(self):
        assert tokenize("123456789") == [T("NUMBER", "123456789", 0)]


class TestOperators:
    def test_single_char_ops(self):
        assert tokenize("+-*/%") == [
            T("OP", "+", 0),
            T("OP", "-", 1),
            T("OP", "*", 2),
            T("OP", "/", 3),
            T("OP", "%", 4),
        ]

    def test_power_is_one_token(self):
        # "**" must be a single token, not two "*" tokens.
        assert tokenize("2 ** 3") == [
            T("NUMBER", "2", 0),
            T("OP", "**", 2),
            T("NUMBER", "3", 5),
        ]

    def test_power_no_spaces(self):
        assert tokenize("2**3") == [
            T("NUMBER", "2", 0),
            T("OP", "**", 1),
            T("NUMBER", "3", 3),
        ]


class TestParens:
    def test_parens(self):
        assert tokenize("()") == [
            T("LPAREN", "(", 0),
            T("RPAREN", ")", 1),
        ]


class TestWhitespace:
    def test_spaces_ignored(self):
        assert tokenize("  1  +   2  ") == [
            T("NUMBER", "1", 2),
            T("OP", "+", 5),
            T("NUMBER", "2", 9),
        ]

    def test_tabs_and_newlines(self):
        # "1\t+\n2" — positions: 0='1', 1='\t', 2='+', 3='\n', 4='2'
        assert tokenize("1\t+\n2") == [
            T("NUMBER", "1", 0),
            T("OP", "+", 2),
            T("NUMBER", "2", 4),
        ]

    def test_empty(self):
        assert tokenize("") == []


class TestTokenShape:
    """Sanity checks on the internal token shape."""

    def test_token_is_tuple_of_three(self):
        toks = tokenize("1 + 2")
        for tok in toks:
            assert isinstance(tok, tuple)
            assert len(tok) == 3

    def test_position_indices(self):
        # Direct positional access works.
        tok = tokenize("42")[0]
        assert tok[_KIND] == "NUMBER"
        assert tok[_VALUE] == "42"
        assert tok[_POSITION] == 0


# ----------------------------------------------------------------------
# Failure cases
# ----------------------------------------------------------------------
class TestErrors:
    def test_trailing_dot(self):
        with pytest.raises(SyntaxError):
            tokenize("1.")

    def test_lone_dot(self):
        with pytest.raises(SyntaxError):
            tokenize(".")

    def test_unknown_character(self):
        with pytest.raises(SyntaxError):
            tokenize("1 + a")

    def test_unknown_symbol(self):
        with pytest.raises(SyntaxError):
            tokenize("1 & 2")

    def test_position_in_error(self):
        with pytest.raises(SyntaxError) as exc:
            tokenize("1 + @")
        # "@" is at index 4 in "1 + @".
        assert "4" in str(exc.value)
