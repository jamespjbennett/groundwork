import pytest
from concept_extractor import extract_concepts


# --- individual concept detection ---

def test_detects_decorator():
    assert "decorator" in extract_concepts("@property\ndef x(self): pass")


def test_detects_dataclass_name_form():
    code = "from dataclasses import dataclass\n@dataclass\nclass Point:\n    x: int"
    concepts = extract_concepts(code)
    assert "dataclass" in concepts
    # @dataclass on a class goes through visit_ClassDef, not visit_FunctionDef,
    # so "decorator" is not emitted — only "dataclass" and "class" are.
    assert "class" in concepts


def test_detects_dataclass_attribute_form():
    code = "import dataclasses\n@dataclasses.dataclass\nclass Point:\n    x: int"
    assert "dataclass" in extract_concepts(code)


def test_detects_list_comprehension():
    assert "list_comprehension" in extract_concepts("r = [x for x in range(10)]")


def test_detects_dict_comprehension():
    assert "dict_comprehension" in extract_concepts("r = {k: v for k, v in d.items()}")


def test_detects_set_comprehension():
    assert "set_comprehension" in extract_concepts("r = {x for x in range(10)}")


def test_detects_generator_expression():
    assert "generator_expression" in extract_concepts("t = sum(x for x in range(10))")


def test_detects_generator_yield():
    assert "generator" in extract_concepts("def g():\n    yield 1")


def test_detects_generator_yield_from():
    assert "generator" in extract_concepts("def g():\n    yield from range(10)")


def test_detects_context_manager():
    assert "context_manager" in extract_concepts("with open('f') as f:\n    pass")


def test_detects_async_context_manager_adds_both_concepts():
    code = "async def f():\n    async with lock:\n        pass"
    concepts = extract_concepts(code)
    assert "context_manager" in concepts
    assert "async_await" in concepts


def test_detects_async_await_via_await_expression():
    code = "async def main():\n    await asyncio.sleep(1)"
    assert "async_await" in extract_concepts(code)


def test_bare_async_def_does_not_emit_async_await():
    # visit_AsyncFunctionDef_async is not a real visitor name; only Await/AsyncWith emit it
    code = "async def main():\n    return 1"
    assert "async_await" not in extract_concepts(code)


def test_detects_class():
    assert "class" in extract_concepts("class Foo:\n    pass")


def test_detects_class_inheritance():
    concepts = extract_concepts("class Bar(Foo):\n    pass")
    assert "class" in concepts
    assert "class_inheritance" in concepts


def test_plain_class_does_not_emit_inheritance():
    assert "class_inheritance" not in extract_concepts("class Foo:\n    pass")


def test_detects_lambda():
    assert "lambda" in extract_concepts("f = lambda x: x + 1")


def test_detects_exception_handling():
    code = "try:\n    pass\nexcept Exception:\n    pass"
    assert "exception_handling" in extract_concepts(code)


def test_detects_import():
    assert "imports" in extract_concepts("import os")


def test_detects_from_import():
    assert "imports" in extract_concepts("from pathlib import Path")


def test_detects_dict_literal():
    assert "dict" in extract_concepts("d = {'a': 1}")


def test_detects_type_hint_subscript():
    assert "type_hints" in extract_concepts("def f(x: list[int]) -> dict[str, int]: ...")


# --- multiple concepts ---

def test_multiple_concepts_in_one_snippet():
    code = (
        "from dataclasses import dataclass\n"
        "@dataclass\n"
        "class Config:\n"
        "    values: list[int]\n"
        "    lookup = {k: v for k, v in {}.items()}\n"
    )
    concepts = extract_concepts(code)
    assert "dataclass" in concepts
    assert "class" in concepts
    assert "dict_comprehension" in concepts
    assert "imports" in concepts


# --- negative / edge cases ---

def test_syntax_error_returns_empty_list():
    assert extract_concepts("def foo(") == []


def test_empty_string_returns_empty_list():
    assert extract_concepts("") == []


def test_plain_expression_with_no_detectable_concept():
    assert extract_concepts("x = 1 + 2") == []


def test_undecorated_function_not_emitted():
    # "function" is in the taxonomy but the visitor only adds "decorator" for decorated fns
    assert extract_concepts("def foo(x):\n    return x") == []
