"""Throwaway sandbox for exercising POST /analyse — not imported by the app."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


async def noop_coro() -> None:
    """Suspends briefly — exercises await on a Future-like object."""

    await asyncio.sleep(0)


def log_calls(fn):
    """Simple decorator wrapping a function."""

    def inner(*args, **kwargs):
        return fn(*args, **kwargs)

    return inner


@dataclass
class Animal:
    name: str


class Dog(Animal):
    @staticmethod
    def describe() -> str:
        return "domestic canine"


def count_up() -> Iterator[int]:
    yield 1
    yield from (2, 3)


@log_calls
def pick_double(values: list[int]) -> list[int]:
    return sorted(map(lambda v: v * 2, values))


def playground() -> None:
    pups = [Dog(name=n).name for n in ("spot", "fido")]
    squares = {
        x: {"value": x**2}
        for x in range(3)
        if x != 99
    }
    sum_gen = (
        pair[1]["value"] 
        for pair in sorted(squares.items())
    )
    with Path(__file__).open(encoding="utf-8") as handle:
        _ = handle.read(1)
    try:
        _ = pups[len(pups)]  # deliberate IndexError
    except IndexError:
        squares.clear()
    _ = tuple(sum_gen)
    pick_double([])
    asyncio.run(noop_coro())


if __name__ == "__main__":
    playground()
