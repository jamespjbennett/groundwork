"""Small calculator for local /analyse testing."""

from __future__ import annotations


class Calculator:
    """Mutable numeric calculator: add, subtract, multiply, divide, reset.

    Also a **context manager**: ``with calc:`` saves ``value`` on entry and
    restores it on exit (even if the block raises), so you can try scratch
    math without losing the outer result. Nested ``with`` uses a stack.
    """

    def __init__(self, start: float = 0.0) -> None:
        self.value = float(start)
        self._checkpoints: list[float] = []

    def __enter__(self) -> Calculator:
        self._checkpoints.append(self.value)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.value = self._checkpoints.pop()

    def reset(self, to: float = 0.0) -> "Calculator":
        self.value = float(to)
        return self

    def add(self, x: float) -> "Calculator":
        self.value += float(x)
        return self

    def sub(self, x: float) -> "Calculator":
        self.value -= float(x)
        return self

    def mul(self, x: float) -> "Calculator":
        self.value *= float(x)
        return self

    def div(self, x: float) -> "Calculator":
        self.value /= float(x)
        return self

    def snapshot(self) -> float:
        return self.value


def demo() -> float:
    calc = Calculator()
    calc.add(10).sub(3).mul(2).div(2)  # 7.0
    with calc:
        calc.reset(0).add(999).mul(2)  # scratch: would be 1998
    return calc.snapshot()  # still 7.0 — checkpoint restored


if __name__ == "__main__":
    print(demo())
