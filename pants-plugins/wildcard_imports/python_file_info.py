import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Tuple

from . import utils


@dataclass(frozen=True)
class PythonImport:
    modules: Tuple[str]
    level: Tuple[int]
    names: Tuple[str]
    aliases: Tuple[str]

    @property
    def is_star_import(self) -> bool:
        return self.names == ("*",)

    @property
    def is_absolute(self) -> bool:
        return self.level == 0

    @property
    def import_str(self) -> str:
        if self.modules_str:
            return f"from {self.modules_str} import {', '.join(self.names)}"
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
    imports: Tuple[PythonImport]
    classes: Tuple[PythonClass]
    functions: Tuple[PythonFunction]
    constants: Tuple[PythonConstant]

    @property
    def file_content_str(self) -> str:
        return self.file_content.decode(encoding="utf-8")

    def uses_import(self, import_str: str) -> bool:
        for import_target in self.imports:
            if import_target.import_str == import_str:
                return True
        return False

    def get_names_used_by_file_target(self, source_file_target: "PythonFileInfo") -> Tuple[str]:
        names = []
        file_content = source_file_target.file_content_str
        for class_target in self.classes:
            if utils.has_symbol_usage(symbol=class_target.name, file_content=file_content):
                names.append(class_target.name)
        for function_target in self.functions:
            if utils.has_symbol_usage(symbol=function_target.name, file_content=file_content):
                names.append(function_target.name)
        for constant_target in self.constants:
            for src_constant in source_file_target.constants:
                if constant_target.name == src_constant.name:
                    break
            else:
                if utils.has_symbol_usage(symbol=constant_target.name, file_content=file_content):
                    names.append(constant_target.name)
        return tuple(names)

    def get_imports_used_by_file_target(self, source_file_target: "PythonFileInfo") -> Tuple[PythonImport]:
        import_targets = []
        for import_target in self.imports:
            names_used = []
            for name in import_target.names:
                if utils.has_symbol_usage(symbol=name, file_content=source_file_target.file_content_str):
                    names_used.append(name)
            if names_used:
                import_targets.append(
                    PythonImport(
                        modules=import_target.modules, level=import_target.level, names=tuple(names_used), aliases=()
                    )
                )
        return tuple(import_targets)


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
            module = node.module.split(".") if node.module else node.module
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
