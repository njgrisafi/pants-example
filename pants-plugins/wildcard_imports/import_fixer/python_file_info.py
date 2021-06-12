import ast
from dataclasses import dataclass
from typing import Iterator, Tuple


@dataclass(frozen=True)
class PythonImport:
    modules: Tuple[str, ...]
    level: int
    names: Tuple[str, ...]
    aliases: Tuple[str, ...]

    @property
    def is_wildcard_import(self) -> bool:
        return self.names == ("*",)

    @property
    def is_absolute(self) -> bool:
        return self.level == 0

    @property
    def import_str(self) -> str:
        if self.modules_str:
            module_str = self.modules_str.replace(".__init__", "")
            return f"from {module_str} import {', '.join(self.names)}"
        return f"import {', '.join(self.names)}"

    @property
    def modules_str(self) -> str:
        return ".".join(self.modules)


@dataclass(frozen=True)
class PythonClass:
    name: str


@dataclass(frozen=True)
class PythonFunction:
    name: str


@dataclass(frozen=True)
class PythonConstant:
    name: str


@dataclass(frozen=True)
class PythonFileInfo:
    path: str
    file_content: bytes
    module_key: str
    imports: Tuple[PythonImport, ...]
    classes: Tuple[PythonClass, ...]
    functions: Tuple[PythonFunction, ...]
    constants: Tuple[PythonConstant, ...]

    @property
    def file_content_str(self) -> str:
        return self.file_content.decode(encoding="utf-8")

    @property
    def is_module(self) -> bool:
        return "__init__.py" in self.path

    def uses_import(self, import_str: str) -> bool:
        for py_import in self.imports:
            if py_import.import_str == import_str:
                return True
        return False

    def has_name(self, name: str) -> bool:
        for py_class in self.classes:
            if name == py_class.name:
                return True
        for py_function in self.functions:
            if name == py_function.name:
                return True
        for py_constant in self.constants:
            if name == py_constant.name:
                return True
        return False


def get_classes_from_ast_node(node: ast.Module) -> Iterator[PythonClass]:
    for node in ast.iter_child_nodes(node):
        if isinstance(node, ast.ClassDef):
            yield PythonClass(name=node.name)


def get_functions_from_ast_node(node: ast.Module) -> Iterator[PythonFunction]:
    for node in ast.iter_child_nodes(node):
        if isinstance(node, ast.FunctionDef):
            yield PythonFunction(node.name)


def get_constants_from_ast_node(node: ast.Module) -> Iterator[PythonConstant]:
    for node in ast.iter_child_nodes(node):
        if isinstance(node, ast.Assign):
            target = node.targets[0]
            if isinstance(target, ast.Name):
                yield PythonConstant(node.targets[0].id)


def get_imports_from_ast_node(node: ast.Module) -> Iterator[PythonImport]:
    for node in ast.iter_child_nodes(node):
        # Handle Class and Function AST
        if isinstance(node, ast.ClassDef):
            results = tuple(get_imports_from_ast_node(node))
            for result in results:
                yield result
        elif isinstance(node, ast.FunctionDef):
            results = tuple(get_imports_from_ast_node(node))
            for result in results:
                yield result

        # Check type of Import node and handle result
        if isinstance(node, ast.Import):
            level = 0
            module = []
        elif isinstance(node, ast.ImportFrom):
            level = node.level
            module = node.module.split(".") if node.module else []
        else:
            continue
        for n in node.names:
            yield PythonImport(modules=tuple(module), level=level, names=tuple(n.name.split(".")), aliases=(n.asname,))


def from_python_file_path(file_path: str, file_content: bytes, module_key: str) -> PythonFileInfo:
    root_node = ast.parse(file_content, file_path)
    return PythonFileInfo(
        path=str(file_path),
        file_content=file_content,
        module_key=module_key,
        imports=tuple(get_imports_from_ast_node(node=root_node)),
        classes=tuple(get_classes_from_ast_node(node=root_node)),
        functions=tuple(get_functions_from_ast_node(node=root_node)),
        constants=tuple(get_constants_from_ast_node(node=root_node)),
    )
