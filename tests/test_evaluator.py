"""End-to-end tests for the public :func:`safeeval.evaluate` API."""

import math

import pytest

from safeeval import evaluate


# ----------------------------------------------------------------------
# Basic operators
# ----------------------------------------------------------------------
class TestBasicOps:
    def test_add(self):
        assert evaluate("1 + 2") == 3.0

    def test_sub(self):
        assert evaluate("5 - 3") == 2.0

    def test_mul(self):
        assert evaluate("4 * 3") == 12.0

    def test_div(self):
        assert evaluate("10 / 4") == 2.5

    def test_mod(self):
        assert evaluate("10 % 3") == 1.0

    def test_pow(self):
        assert evaluate("2 ** 8") == 256.0


class TestPrecedence:
    def test_mul_before_add(self):
        assert evaluate("1 + 2 * 3") == 7.0

    def test_div_before_sub(self):
        assert evaluate("10 - 6 / 2") == 7.0

    def test_pow_before_mul(self):
        assert evaluate("2 * 3 ** 2") == 18.0

    def test_pow_right_associative(self):
        # 2 ** 3 ** 2 == 2 ** (3 ** 2) == 2 ** 9 == 512
        assert evaluate("2 ** 3 ** 2") == 512.0

    def test_pow_left_associative_chain(self):
        # ((2**3)**2) = 64
        assert evaluate("(2 ** 3) ** 2") == 64.0

    def test_parens_override(self):
        assert evaluate("(1 + 2) * 3") == 9.0

    def test_nested_parens(self):
        assert evaluate("((1 + 2) * (3 + 4))") == 21.0


# ----------------------------------------------------------------------
# Unary
# ----------------------------------------------------------------------
class TestUnary:
    def test_unary_minus(self):
        assert evaluate("-5") == -5.0

    def test_unary_plus(self):
        assert evaluate("+5") == 5.0

    def test_double_unary(self):
        assert evaluate("--5") == 5.0

    def test_unary_in_expression(self):
        assert evaluate("3 + -2") == 1.0

    def test_unary_binds_looser_than_pow(self):
        # Python: -2 ** 2 == -(2**2) == -4
        assert evaluate("-2 ** 2") == -4.0

    def test_unary_minus_then_pow_right_assoc(self):
        # -2 ** 3 ** 2 == -(2 ** (3 ** 2)) == -512
        assert evaluate("-2 ** 3 ** 2") == -512.0

    def test_unary_inside_parens(self):
        # (-2) ** 2 == 4
        assert evaluate("(-2) ** 2") == 4.0


# ----------------------------------------------------------------------
# Numbers
# ----------------------------------------------------------------------
class TestNumbers:
    def test_float_literal(self):
        assert evaluate("0.1 + 0.2") == pytest.approx(0.3)

    def test_leading_dot(self):
        assert evaluate(".5 + .25") == 0.75

    def test_negative_result(self):
        assert evaluate("1 - 2") == -1.0

    def test_zero(self):
        assert evaluate("0") == 0.0

    def test_large_number(self):
        assert evaluate("123456789") == 123456789.0


# ----------------------------------------------------------------------
# Whitespace
# ----------------------------------------------------------------------
class TestWhitespace:
    def test_no_spaces(self):
        assert evaluate("1+2*3") == 7.0

    def test_lots_of_spaces(self):
        assert evaluate("   1   +   2   ") == 3.0

    def test_newlines(self):
        assert evaluate("1\n+\n2") == 3.0


# ----------------------------------------------------------------------
# Errors
# ----------------------------------------------------------------------
class TestSyntaxErrors:
    def test_empty(self):
        with pytest.raises(SyntaxError):
            evaluate("")

    def test_whitespace_only(self):
        with pytest.raises(SyntaxError):
            evaluate("   ")

    def test_trailing_operator(self):
        with pytest.raises(SyntaxError):
            evaluate("1 +")

    def test_leading_unary_plus_is_valid(self):
        # "+1" is a unary plus followed by a number; legal.
        assert evaluate("+ 1") == 1.0

    def test_leading_unary_minus_is_valid(self):
        assert evaluate("-1") == -1.0

    def test_only_binary_plus_is_error(self):
        # "+ 1 +" is a unary plus on "1", then trailing binary +.
        with pytest.raises(SyntaxError):
            evaluate("+ 1 +")

    def test_two_operators(self):
        with pytest.raises(SyntaxError):
            evaluate("1 + * 2")

    def test_unmatched_open_paren(self):
        with pytest.raises(SyntaxError):
            evaluate("(1 + 2")

    def test_unmatched_close_paren(self):
        with pytest.raises(SyntaxError):
            evaluate("1 + 2)")

    def test_empty_parens(self):
        with pytest.raises(SyntaxError):
            evaluate("()")

    def test_adjacent_numbers(self):
        with pytest.raises(SyntaxError):
            evaluate("1 2")

    def test_trailing_dot(self):
        with pytest.raises(SyntaxError):
            evaluate("1. + 2")

    def test_unknown_character(self):
        with pytest.raises(SyntaxError):
            evaluate("1 + a")

    def test_unknown_operator(self):
        with pytest.raises(SyntaxError):
            evaluate("1 & 2")

    def test_paren_then_eof(self):
        with pytest.raises(SyntaxError):
            evaluate("(")

    def test_double_binary_op(self):
        with pytest.raises(SyntaxError):
            evaluate("1 ** ** 2")

    def test_closing_paren_after_binary(self):
        with pytest.raises(SyntaxError):
            evaluate("1 + )")


class TestZeroDivision:
    def test_div_by_zero(self):
        with pytest.raises(ZeroDivisionError):
            evaluate("1 / 0")

    def test_mod_by_zero(self):
        with pytest.raises(ZeroDivisionError):
            evaluate("1 % 0")

    def test_complex_expr_with_div_zero(self):
        with pytest.raises(ZeroDivisionError):
            # 4 - 4 == 0, then 1 / 0
            evaluate("2 + 3 * (1 / (4 - 4))")

    def test_zero_pow_negative(self):
        with pytest.raises(ZeroDivisionError):
            evaluate("0 ** -1")


# ----------------------------------------------------------------------
# Floating point and tricky values
# ----------------------------------------------------------------------
class TestFloats:
    def test_division_produces_float(self):
        result = evaluate("1 / 3")
        assert isinstance(result, float)
        assert result == pytest.approx(0.3333333333, rel=1e-9)

    def test_sqrt_via_pow(self):
        # 2 ** 0.5
        assert evaluate("2 ** 0.5") == pytest.approx(math.sqrt(2))

    def test_associativity_float(self):
        # Floats are not associative, but our parser mirrors Python's
        # left-associative behaviour for the same expression form.
        assert evaluate("1.0 + 2.0 + 3.0") == 6.0

    def test_integer_pow_with_negative_exponent(self):
        # 2 ** -1 == 0.5
        assert evaluate("2 ** -1") == 0.5

    def test_negative_base_fractional_exponent_is_value_error(self):
        # Python: (-1.0) ** 0.5 -> complex; we surface that as ValueError.
        with pytest.raises(ValueError):
            evaluate("(-1) ** 0.5")
