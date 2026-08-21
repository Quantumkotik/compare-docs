"""Безопасное вычисление арифметических выражений."""

from __future__ import annotations

import ast
import operator

BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class ОшибкаВыражения(Exception):
    """Выражение некорректно или содержит недопустимые операции."""


def _вычислить_узел(узел: ast.AST) -> float:
    if isinstance(узел, ast.Expression):
        return _вычислить_узел(узел.body)

    if isinstance(узел, ast.Constant):
        if isinstance(узел.value, bool) or not isinstance(узел.value, (int, float)):
            raise ОшибкаВыражения("Допустимы только числа")
        return узел.value

    if isinstance(узел, ast.BinOp):
        операция = BINARY_OPS.get(type(узел.op))
        if операция is None:
            raise ОшибкаВыражения("Недопустимая операция")
        левый = _вычислить_узел(узел.left)
        правый = _вычислить_узел(узел.right)

        # ограничение степени: 9**9**9 иначе намертво подвесит окно
        if isinstance(узел.op, ast.Pow) and (abs(правый) > 1000 or abs(левый) > 1e12):
            raise ОшибкаВыражения("Слишком большая степень")

        try:
            return операция(левый, правый)
        except ZeroDivisionError:
            raise ОшибкаВыражения("Деление на ноль") from None
        except OverflowError:
            raise ОшибкаВыражения("Слишком большое число") from None

    if isinstance(узел, ast.UnaryOp):
        операция = UNARY_OPS.get(type(узел.op))
        if операция is None:
            raise ОшибкаВыражения("Недопустимая операция")
        return операция(_вычислить_узел(узел.operand))

    raise ОшибкаВыражения("Недопустимое выражение")


def вычислить(выражение: str) -> float:
    """Вычисляет арифметическое выражение: + - * / % ** и скобки."""
    текст = выражение.replace(",", ".").replace("×", "*").replace("÷", "/").replace("−", "-")

    if not текст.strip():
        raise ОшибкаВыражения("Пустое выражение")

    try:
        дерево = ast.parse(текст, mode="eval")
    except SyntaxError:
        raise ОшибкаВыражения("Некорректное выражение") from None

    результат = _вычислить_узел(дерево)

    if результат != результат or результат in (float("inf"), float("-inf")):
        raise ОшибкаВыражения("Результат не определён")

    return результат


def форматировать(число: float) -> str:
    """Убирает лишний хвост у дробей: 4.0 -> 4, 0.30000000000000004 -> 0.3."""
    if isinstance(число, int) or число == int(число):
        return str(int(число))
    return f"{число:.10g}"
