import ast
import json
from pathlib import Path

_taxonomy_path = Path(__file__).parent / "taxonomy.json"
_taxonomy: list[dict] = json.loads(_taxonomy_path.read_text()) if _taxonomy_path.exists() else []
_taxonomy_ids = {entry["id"] for entry in _taxonomy}


def extract_concepts(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    found: set[str] = set()
    visitor = _ConceptVisitor(found)
    visitor.visit(tree)
    return [c for c in found if c in _taxonomy_ids]


class _ConceptVisitor(ast.NodeVisitor):
    def __init__(self, found: set[str]):
        self.found = found

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.decorator_list:
            self.found.add("decorator")
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ListComp(self, node: ast.ListComp):
        self.found.add("list_comprehension")
        self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp):
        self.found.add("dict_comprehension")
        self.generic_visit(node)

    def visit_SetComp(self, node: ast.SetComp):
        self.found.add("set_comprehension")
        self.generic_visit(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp):
        self.found.add("generator_expression")
        self.generic_visit(node)

    def visit_With(self, node: ast.With):
        self.found.add("context_manager")
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith):
        self.found.add("context_manager")
        self.found.add("async_await")
        self.generic_visit(node)

    def visit_Yield(self, node: ast.Yield):
        self.found.add("generator")
        self.generic_visit(node)

    def visit_YieldFrom(self, node: ast.YieldFrom):
        self.found.add("generator")
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.found.add("class")
        if node.bases:
            self.found.add("class_inheritance")
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
                self.found.add("dataclass")
            elif isinstance(decorator, ast.Attribute) and decorator.attr == "dataclass":
                self.found.add("dataclass")
        self.generic_visit(node)

    def visit_Lambda(self, node: ast.Lambda):
        self.found.add("lambda")
        self.generic_visit(node)

    def visit_AsyncFunctionDef_async(self, node):
        self.found.add("async_await")
        self.generic_visit(node)

    def visit_Await(self, node: ast.Await):
        self.found.add("async_await")
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try):
        self.found.add("exception_handling")
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        self.found.add("imports")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        self.found.add("imports")
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict):
        self.found.add("dict")
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript):
        # rough heuristic for type hints / generics
        if isinstance(node.ctx, ast.Load):
            self.found.add("type_hints")
        self.generic_visit(node)
