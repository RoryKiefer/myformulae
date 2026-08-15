"""Algebra engine: parses input and produces step-by-step algebra solutions using SymPy.

Only a single variable, ``x``, is supported. Three modes are exposed:

- ``solve_equation``    -- solve "expr = expr" for x
- ``simplify_expression`` -- combine like terms / expand
- ``factor_expression``  -- factor a polynomial in x

Step-by-step explanations are hand-written for the common homework cases
(linear equations, quadratics, common-factor/difference-of-squares/trinomial
factoring, combining like terms). Anything outside those patterns still gets
a correct final answer from SymPy, with a note that steps aren't available.
"""
import ast
import math
import re
from dataclasses import dataclass, field
from io import StringIO
from tokenize import (
    ENCODING,
    ENDMARKER,
    NAME,
    NEWLINE,
    NL,
    NUMBER,
    OP,
    TokenError,
    generate_tokens,
    untokenize,
)
from typing import List

import sympy
from sympy import (
    Eq,
    Float,
    Integer,
    Poly,
    Pow,
    Symbol,
    cancel,
    expand,
    factor,
    factor_list,
    latex,
    simplify,
    solve,
    sqrt,
)
from sympy.core.traversal import preorder_traversal

x = Symbol("x")

_MAX_INPUT_LEN = 200
_MAX_INT_DIGITS = 10
_MAX_EXPONENT = 10
_MAX_NODES = 80

_ALLOWED_OPS = frozenset({"+", "-", "*", "/", "**", "^", "(", ")"})
_NUMBER_RE = re.compile(r"^\d+(\.\d*)?$|^\.\d+$")
_SKIP_TOKEN_TYPES = {ENCODING, NEWLINE, NL, ENDMARKER}


class AlgebraError(ValueError):
    """Raised when input can't be parsed or otherwise isn't a valid single-variable-in-x problem."""


@dataclass
class Result:
    mode: str
    input_display: str
    final: str
    steps: List[str] = field(default_factory=list)
    note: str = ""


def _parse_error(expr_str: str) -> AlgebraError:
    return AlgebraError(f"Could not parse '{expr_str}' as a math expression.")


def _needs_implicit_mul(prev: tuple, curr: tuple) -> bool:
    prev_type, prev_val = prev
    curr_type, curr_val = curr
    if prev_type in {NUMBER, NAME} and curr_type == NAME:
        return True
    if prev_type in {NUMBER, NAME} and curr_type == OP and curr_val == "(":
        return True
    if prev_type == OP and prev_val == ")" and curr_type in {NAME, NUMBER}:
        return True
    if prev_type == OP and prev_val == ")" and curr_type == OP and curr_val == "(":
        return True
    return False


def _check_number_token(token: str, expr_str: str) -> None:
    if not _NUMBER_RE.fullmatch(token):
        raise _parse_error(expr_str)
    digits = token.replace(".", "")
    if len(digits) > _MAX_INT_DIGITS:
        raise AlgebraError("Number is too large.")


def _to_python_expr(expr_str: str) -> str:
    """Turn a homework expression into Python arithmetic, rejecting anything else.

    Only ``x``, decimal numbers, and ``+ - * / ** ^ ( )`` are allowed. Implicit
    multiplication (``2x``, ``2(x+1)``) is inserted here so we never hand the
    string to SymPy's ``parse_expr`` / ``eval``.
    """
    try:
        raw = list(generate_tokens(StringIO(expr_str).readline))
    except TokenError as e:
        raise _parse_error(expr_str) from e

    tokens: List[tuple] = []
    prev = None
    for tok in raw:
        if tok.type in _SKIP_TOKEN_TYPES:
            continue
        if tok.type == NAME:
            if tok.string != "x":
                raise AlgebraError(f"Only 'x' may be used as a variable (found: {tok.string}).")
            pair = (NAME, "x")
        elif tok.type == OP:
            if tok.string not in _ALLOWED_OPS:
                raise _parse_error(expr_str)
            pair = (OP, "**" if tok.string == "^" else tok.string)
        elif tok.type == NUMBER:
            _check_number_token(tok.string, expr_str)
            pair = (NUMBER, tok.string)
        else:
            raise _parse_error(expr_str)

        if prev is not None and _needs_implicit_mul(prev, pair):
            tokens.append((OP, "*"))
        tokens.append(pair)
        prev = pair

    if not tokens:
        raise AlgebraError("Expression is empty.")
    return untokenize(tokens)


def _safe_pow(base, exp):
    if exp.is_number:
        try:
            mag = abs(float(exp))
        except (TypeError, ValueError, OverflowError):
            raise AlgebraError("Exponent is too large.")
        if not math.isfinite(mag) or mag > _MAX_EXPONENT:
            raise AlgebraError("Exponent is too large.")
    elif any(getattr(node, "is_Pow", False) for node in preorder_traversal(exp)):
        raise AlgebraError("Expression is too complex.")
    return Pow(base, exp, evaluate=False)


def _ast_to_expr(node, expr_str: str, stats: List[int]):
    stats[0] += 1
    if stats[0] > _MAX_NODES:
        raise AlgebraError("Expression is too complex.")

    if isinstance(node, ast.Expression):
        return _ast_to_expr(node.body, expr_str, stats)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise _parse_error(expr_str)
        if isinstance(node.value, int):
            if abs(node.value) >= 10 ** _MAX_INT_DIGITS:
                raise AlgebraError("Number is too large.")
            return Integer(node.value)
        if not math.isfinite(node.value) or abs(node.value) >= 10 ** _MAX_INT_DIGITS:
            raise AlgebraError("Number is too large.")
        return Float(node.value)
    if isinstance(node, ast.UnaryOp):
        operand = _ast_to_expr(node.operand, expr_str, stats)
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, ast.USub):
            return -operand
        raise _parse_error(expr_str)
    if isinstance(node, ast.BinOp):
        left = _ast_to_expr(node.left, expr_str, stats)
        right = _ast_to_expr(node.right, expr_str, stats)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return _safe_pow(left, right)
        raise _parse_error(expr_str)
    if isinstance(node, ast.Name):
        if node.id == "x":
            return x
        raise AlgebraError(f"Only 'x' may be used as a variable (found: {node.id}).")
    raise _parse_error(expr_str)


def _parse(expr_str: str):
    expr_str = expr_str.strip()
    if not expr_str:
        raise AlgebraError("Expression is empty.")
    if len(expr_str) > _MAX_INPUT_LEN:
        raise AlgebraError("Expression is too long.")
    try:
        code = _to_python_expr(expr_str)
        tree = ast.parse(code, mode="eval")
        expr = _ast_to_expr(tree, expr_str, [0])
    except AlgebraError:
        raise
    except (SyntaxError, ValueError, RecursionError, MemoryError, OverflowError) as e:
        raise _parse_error(expr_str) from e
    free = expr.free_symbols
    if free - {x}:
        extra = ", ".join(sorted(str(s) for s in free - {x}))
        raise AlgebraError(f"Only 'x' may be used as a variable (found: {extra}).")
    return expr


def detect_mode(text: str) -> str:
    return "solve" if "=" in text else "simplify"


# ---------------------------------------------------------------- solve ----

def solve_equation(text: str) -> Result:
    if text.count("=") != 1:
        raise AlgebraError("An equation must contain exactly one '='.")
    lhs_str, rhs_str = text.split("=", 1)
    lhs, rhs = _parse(lhs_str), _parse(rhs_str)

    input_display = f"{latex(lhs)} = {latex(rhs)}"
    moved = expand(lhs - rhs)

    if moved == 0:
        return Result(
            "solve",
            input_display,
            "\\text{Infinitely many solutions}",
            [f"{latex(lhs)} = {latex(rhs)}", "0 = 0"],
            note="Both sides are always equal — every value of x is a solution.",
        )

    try:
        poly = Poly(moved, x) if moved.has(x) else None
    except sympy.PolynomialError:
        poly = None

    if poly is not None and poly.degree() == 1:
        steps, sols = _solve_linear_steps(lhs, rhs)
        final = ", ".join(f"x = {latex(s)}" for s in sols)
        return Result("solve", input_display, final, steps)

    if poly is not None and poly.degree() == 2:
        steps, sols = _solve_quadratic_steps(poly)
        final = ", ".join(f"x = {latex(s)}" for s in sols) if sols else "\\text{No real solutions}"
        return Result("solve", input_display, final, steps)

    sols = solve(Eq(lhs, rhs), x)
    final = ", ".join(f"x = {latex(s)}" for s in sols) if sols else "\\text{No solution}"
    return Result(
        "solve", input_display, final, [],
        note="Step-by-step isn't available for this equation yet — showing the final answer only.",
    )


def _solve_linear_steps(lhs, rhs) -> "tuple[List[str], list]":
    steps = [f"{latex(lhs)} = {latex(rhs)}"]

    exp_lhs, exp_rhs = expand(lhs), expand(rhs)
    if exp_lhs != lhs or exp_rhs != rhs:
        steps.append(f"{latex(exp_lhs)} = {latex(exp_rhs)}")

    moved = expand(exp_lhs - exp_rhs)  # a*x + b == 0
    a = moved.coeff(x, 1)
    b = moved.coeff(x, 0)

    steps.append(f"{latex(a * x + b)} = 0")

    if b != 0:
        steps.append(f"{latex(a * x)} = {latex(-b)}")

    sol = simplify(-b / a)
    if a != 1:
        steps.append(f"x = \\frac{{{latex(-b)}}}{{{latex(a)}}}")
    final_step = f"x = {latex(sol)}"
    if steps[-1] != final_step:
        steps.append(final_step)
    return steps, [sol]


def _solve_quadratic_steps(poly: Poly) -> "tuple[List[str], list]":
    a, b, c = poly.all_coeffs()
    lhs_expr = a * x**2 + b * x + c
    steps = [f"{latex(lhs_expr)} = 0"]

    discriminant = simplify(b**2 - 4 * a * c)
    steps.append(
        f"x = \\frac{{-({latex(b)}) \\pm \\sqrt{{({latex(b)})^2 - 4({latex(a)})({latex(c)})}}}}{{2({latex(a)})}}"
    )
    steps.append(f"x = \\frac{{{latex(-b)} \\pm \\sqrt{{{latex(discriminant)}}}}}{{{latex(2 * a)}}}")

    if discriminant < 0:
        return steps, []

    sqrt_d = sqrt(discriminant)
    sol1 = simplify((-b + sqrt_d) / (2 * a))
    sol2 = simplify((-b - sqrt_d) / (2 * a))
    sols = [sol1] if sol1 == sol2 else [sol1, sol2]
    steps.append(", ".join(f"x = {latex(s)}" for s in sols))
    return steps, sols


# ------------------------------------------------------------- simplify ----

def simplify_expression(text: str) -> Result:
    """Combine like terms / reduce rational expressions.

    Deliberately avoids sympy's general-purpose ``simplify()``, which will
    happily factor a polynomial (e.g. 2x^2+2x -> 2x(x+1)) — not what a
    student means by "simplify" for this mode; factoring has its own tab.
    """
    expr = _parse(text)
    input_display = latex(expr)

    steps = [latex(expr)]
    expanded = expand(expr)
    if expanded != expr:
        steps.append(latex(expanded))

    final_expr = cancel(expanded)
    if final_expr != expanded:
        steps.append(latex(final_expr))

    # de-duplicate consecutive identical steps
    dedup: List[str] = []
    for s in steps:
        if not dedup or dedup[-1] != s:
            dedup.append(s)

    return Result("simplify", input_display, latex(final_expr), dedup)


# --------------------------------------------------------------- factor ----

def factor_expression(text: str) -> Result:
    expr = _parse(text)
    input_display = latex(expr)
    expr = expand(expr)

    steps = [latex(expr)]

    content, _factors = factor_list(expr)
    if expr.has(x) and content != 1 and content != -1:
        remaining = expr / content
        steps.append(f"{latex(content)}\\left({latex(expand(remaining))}\\right)")

    final = factor(expr)
    if latex(final) != steps[-1]:
        steps.append(latex(final))

    dedup: List[str] = []
    for s in steps:
        if not dedup or dedup[-1] != s:
            dedup.append(s)

    note = ""
    if final == expr and not expr.is_number:
        note = "This expression doesn't factor further over the rationals."

    return Result("factor", input_display, latex(final), dedup, note)


_MODES = {
    "solve": solve_equation,
    "simplify": simplify_expression,
    "factor": factor_expression,
}


def run(mode: str, text: str) -> Result:
    if mode not in _MODES:
        raise AlgebraError(f"Unknown mode: {mode}")
    return _MODES[mode](text)
