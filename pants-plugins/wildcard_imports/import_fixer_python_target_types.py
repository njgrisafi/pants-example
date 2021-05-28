import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List

from . import import_fixer_utils


@dataclass
class ImportTarget:
    modules: List[str]
    level: List[int]
    names: List[str]
    aliases: List[str]

    @property
    def is_star_import(self) -> bool:
        return self.names == ["*"]

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


@dataclass
class ClassTarget:
    name: str


@dataclass
class FunctionTarget:
    name: str


@dataclass
class ConstantTarget:
    name: str


@dataclass
class FileTarget:
    path: str
    module_key: str
    imports: List[ImportTarget]
    classes: List[ClassTarget]
    functions: List[FunctionTarget]
    constants: List[ConstantTarget]

    @property
    def file_content_bytes(self) -> bytes:
        return Path(self.path).read_bytes()

    @property
    def file_content_str(self) -> str:
        return Path(self.path).read_text()

    def uses_import(self, import_str: str) -> bool:
        for import_target in self.imports:
            if import_target.import_str == import_str:
                return True
        return False

    def get_names_used_by_file_target(self, source_file_target: "FileTarget") -> List[str]:
        names = []
        file_content = source_file_target.file_content_str
        for class_target in self.classes:
            if import_fixer_utils.has_symbol_usage(symbol=class_target.name, file_content=file_content):
                names.append(class_target.name)
        for function_target in self.functions:
            if import_fixer_utils.has_symbol_usage(symbol=function_target.name, file_content=file_content):
                names.append(function_target.name)
        for constant_target in self.constants:
            for src_constant in source_file_target.constants:
                if constant_target.name == src_constant.name:
                    break
            else:
                if import_fixer_utils.has_symbol_usage(symbol=constant_target.name, file_content=file_content):
                    names.append(constant_target.name)
        return names

    def get_imports_used_by_file_target(self, source_file_target: "FileTarget") -> List[ImportTarget]:
        import_targets = []
        for import_target in self.imports:
            names_used = []
            for name in import_target.names:
                if import_fixer_utils.has_symbol_usage(symbol=name, file_content=source_file_target.file_content_str):
                    names_used.append(name)
            if names_used:
                import_targets.append(
                    ImportTarget(modules=import_target.modules, level=import_target.level, names=names_used, aliases=[])
                )
        return import_targets


def get_classes_from_ast_node(node: ast.Module) -> Iterator[ClassTarget]:
    for node in ast.iter_child_nodes(node):
        if isinstance(node, ast.ClassDef):
            yield ClassTarget(name=node.name)


def get_functions_from_ast_node(node: ast.Module) -> Iterator[FunctionTarget]:
    for node in ast.iter_child_nodes(node):
        if isinstance(node, ast.FunctionDef):
            yield FunctionTarget(node.name)


def get_constants_from_ast_node(node: ast.Module) -> Iterator[ConstantTarget]:
    for node in ast.iter_child_nodes(node):
        if isinstance(node, ast.Assign):
            target = node.targets[0]
            if isinstance(target, ast.Name):
                yield ConstantTarget(node.targets[0].id)


def get_imports_from_ast_node(node: ast.Module) -> Iterator[ImportTarget]:
    for node in ast.iter_child_nodes(node):
        # Handle Class and Function AST
        if isinstance(node, ast.ClassDef):
            results = list(get_imports_from_ast_node(node))
            for result in results:
                yield result
        elif isinstance(node, ast.FunctionDef):
            results = list(get_imports_from_ast_node(node))
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
            yield ImportTarget(modules=module, level=level, names=n.name.split("."), aliases=n.asname)


def from_python_file_path(file_path: Path, module_key: str) -> FileTarget:
    with file_path.open() as fh:
        root_node = ast.parse(fh.read(), str(file_path))
    return FileTarget(
        path=str(file_path),
        module_key=module_key,
        imports=list(get_imports_from_ast_node(node=root_node)),
        classes=list(get_classes_from_ast_node(node=root_node)),
        functions=list(get_functions_from_ast_node(node=root_node)),
        constants=list(get_constants_from_ast_node(node=root_node)),
    )
