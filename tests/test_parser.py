"""Tests for the parser internals (called via tokenizer + parser)."""

import pytest

from safeeval._parser import parse
from safeeval._tokenizer import tokenize


def parse_str(s: str) -> float:
    return parse(tokenize(s))


class TestDirectParser:
    def test_simple(self):
        assert parse_str("1 + 2") == 3.0

    def test_nested(self):
        assert parse_str("((2 + 3) * (4 - 1))") == 15.0

    def test_empty_token_list_is_error(self):
        with pytest.raises(SyntaxError):
            parse([])

    def test_only_operator_is_error(self):
        with pytest.raises(SyntaxError):
            parse_str("+")

    def test_unmatched_paren_error(self):
        with pytest.raises(SyntaxError):
            parse_str("(1 + 2")


class TestParserRandom:
    """Cross-check our parser against Python's eval for a battery of
    arithmetic expressions. ``eval`` here is a test-time sanity check
    only and is never used by the library itself."""

    cases = [
        "0",
        "1",
        "1 + 2",
        "1 - 2 - 3",
        "1 - (2 - 3)",
        "2 * 3 + 4",
        "2 + 3 * 4",
        "(2 + 3) * 4",
        "1 / 2",
        "1 / 2 / 4",
        "1 / (2 / 4)",
        "8 % 3",
        "(8 % 3) + 1",
        "2 ** 3",
        "2 ** 3 ** 2",
        "(2 ** 3) ** 2",
        "10 - 2 ** 3",
        "(10 - 2) ** 3",
        "-1",
        "--1",
        "---1",
        "+1",
        "-1 + 2",
        "1 + -2",
        "1 - -2",
        "-(1 + 2)",
        "-1 ** 2",
        "(-1) ** 2",
        "1.5 * 2",
        ".5 * 2",
        "2 * .5",
        "0.1 + 0.2",
        "((1))",
        "(((1 + 2)))",
        "1 + 2 * 3 - 4 / 2 + 5 % 3",
        "2 ** (1 + 2)",
        "(2 ** 1) + 2",
        "1 + 2 * 3 ** 2 - 1",
        "-2 ** 2 ** 2",
        "(-2) ** 2 ** 2",
    ]

    @pytest.mark.parametrize("expr", cases)
    def test_matches_python_eval(self, expr):
        assert parse_str(expr) == pytest.approx(eval(expr))
