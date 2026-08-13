import pytest

from algebra.engine import (
    AlgebraError,
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
