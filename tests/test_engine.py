import pytest

from algebra.engine import (
    AlgebraError,
    _MAX_EXPONENT,
    _MAX_INPUT_LEN,
    _MAX_INT_DIGITS,
    detect_mode,
    factor_expression,
    simplify_expression,
    solve_equation,
)


def test_detect_mode():
    assert detect_mode("2*x + 3 = 7") == "solve"
    assert detect_mode("x**2 + 2*x") == "simplify"


def test_solve_linear():
    result = solve_equation("2*x + 3 = 7")
    assert result.final == "x = 2"
    assert len(result.steps) >= 2


def test_solve_linear_variables_both_sides():
    result = solve_equation("3*x - 5 = 2*x + 10")
    assert result.final == "x = 15"


def test_solve_quadratic_two_real_roots():
    result = solve_equation("x^2 - 5*x + 6 = 0")
    assert "x = 3" in result.final
    assert "x = 2" in result.final


def test_solve_quadratic_no_real_roots():
    result = solve_equation("x^2 + 4 = 0")
    assert result.final == "\\text{No real solutions}"


def test_solve_requires_equals_sign():
    with pytest.raises(AlgebraError):
        solve_equation("2*x + 3")


def test_simplify_combines_like_terms():
    result = simplify_expression("x**2 + 2*x + x**2")
    assert result.final == "2 x^{2} + 2 x"


def test_simplify_does_not_factor():
    result = simplify_expression("2*x^2 + 4*x")
    assert "(" not in result.final


def test_simplify_cancels_rational_expression():
    result = simplify_expression("(x**2 - 1)/(x - 1)")
    assert result.final == "x + 1"


def test_factor_difference_of_squares():
    result = factor_expression("x^2 - 4")
    assert result.final == "\\left(x - 2\\right) \\left(x + 2\\right)"


def test_factor_common_factor():
    result = factor_expression("2*x^2 + 4*x")
    assert result.final == "2 x \\left(x + 2\\right)"


def test_factor_irreducible_has_note():
    result = factor_expression("x^2 + 1")
    assert result.note != ""


def test_rejects_other_variables():
    with pytest.raises(AlgebraError):
        solve_equation("2*x + y = 7")


def test_rejects_empty_input():
    with pytest.raises(AlgebraError):
        simplify_expression("   ")


def test_rejects_garbage_input():
    with pytest.raises(AlgebraError):
        simplify_expression("2 + + x *")


def test_implicit_multiplication():
    assert simplify_expression("2x + 3").final == "2 x + 3"
    assert simplify_expression("2(x+1)").final == "2 x + 2"
    assert simplify_expression("x(x+1)").final == "x^{2} + x"
    assert simplify_expression("(x+1)(x-1)").final == "x^{2} - 1"
    assert simplify_expression("(x+1)2").final == "2 x + 2"


def test_unary_signs_and_decimals():
    assert simplify_expression("-x + +x").final == "0"
    assert simplify_expression("1.5*x + 0.5*x").final == "2.0 x"


@pytest.mark.parametrize(
    "text",
    [
        "abs(1)",
        "True",
        "__import__",
        "open",
        "x.__class__",
        "lambda x: x",
        "1 if 1 else 0",
        "x[0]",
    ],
)
def test_rejects_python_evaluation(text):
    with pytest.raises(AlgebraError):
        simplify_expression(text)


@pytest.mark.parametrize("text", ["1e99", "0x10", "0b10", "0o10", "2j", "1_000"])
def test_rejects_non_decimal_numbers(text):
    with pytest.raises(AlgebraError):
        simplify_expression(text)


@pytest.mark.parametrize("text", ["x % 2", "x << 1", "x & 1", "~x", "5!", "'x'", "x + 1 # c"])
def test_rejects_non_arithmetic_tokens(text):
    with pytest.raises(AlgebraError):
        simplify_expression(text)


def test_rejects_unbalanced_parentheses():
    with pytest.raises(AlgebraError):
        simplify_expression("(x+1")


def test_rejects_input_over_length_limit():
    with pytest.raises(AlgebraError, match="too long"):
        simplify_expression("x" * (_MAX_INPUT_LEN + 1))


def test_integer_digit_limit():
    n = "1" * _MAX_INT_DIGITS
    assert simplify_expression(n).final == n
    with pytest.raises(AlgebraError, match="too large"):
        simplify_expression("1" * (_MAX_INT_DIGITS + 1))


def test_exponent_limit():
    assert simplify_expression(f"x**{_MAX_EXPONENT}").final == f"x^{{{_MAX_EXPONENT}}}"
    with pytest.raises(AlgebraError, match="too large"):
        simplify_expression(f"x**{_MAX_EXPONENT + 1}")
    with pytest.raises(AlgebraError, match="too large"):
        simplify_expression("10**99")


def test_rejects_nested_exponentiation():
    with pytest.raises(AlgebraError, match="too complex"):
        simplify_expression("x**(x**2)")
    with pytest.raises(AlgebraError, match="too complex"):
        simplify_expression("2**(2**x)")


def test_rejects_expression_that_is_too_complex():
    with pytest.raises(AlgebraError, match="too complex"):
        simplify_expression("+".join(["x"] * 50))
