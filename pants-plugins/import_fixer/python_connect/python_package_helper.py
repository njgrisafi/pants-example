from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Tuple

from import_fixer.python_connect import python_utils
from import_fixer.python_connect.python_file_info import PythonFileInfo, PythonImport, from_python_file_path
from pants.engine.fs import DigestContents
from pants.util.frozendict import FrozenDict


@dataclass(frozen=True)
class PythonPackageHelper:
    include_top_level_package: bool
    py_file_info_by_module: FrozenDict[str, PythonFileInfo]
    py_file_info_by_import_module_str: FrozenDict[str, Tuple[PythonFileInfo, ...]]
    ignored_import_names_by_module: FrozenDict[str, Tuple[str, ...]]

    def get_python_file_info_from_file_path(self, file_path: str) -> PythonFileInfo:
        module_key = python_utils.generate_relative_module_key(
            py_file_path=file_path, include_top_level_package=self.include_top_level_package
        )
        return self.py_file_info_by_module[module_key]

    def get_transitive_python_files(self, source_py_file_info: PythonFileInfo) -> Tuple[PythonFileInfo, ...]:
        return self.py_file_info_by_import_module_str.get(source_py_file_info.module_key, ())

    def is_package_import(self, py_import: PythonImport) -> bool:
        return bool(self.py_file_info_by_module.get(py_import.modules_str))


def unwind_relative_imports(py_file_info_by_module: Dict[str, PythonFileInfo]) -> Dict[str, PythonFileInfo]:
    for module_key in py_file_info_by_module:
        for i in range(len(py_file_info_by_module[module_key].imports)):
            existing_file_info = py_file_info_by_module[module_key]
            current_import = existing_file_info.imports[i]
            if current_import.is_absolute is False and current_import.modules is not None:
                fixed_file_info_imports = list(py_file_info_by_module[module_key].imports)
                fixed_file_info_imports[i] = PythonImport(
                    modules=tuple(module_key.split(".")[: (-1 * current_import.level)]) + current_import.modules,
                    level=0,
                    names=current_import.names,
                    aliases=current_import.aliases,
                )
                py_file_info_by_module[module_key] = PythonFileInfo(
                    path=existing_file_info.path,
                    file_content=existing_file_info.file_content,
                    module_key=existing_file_info.module_key,
                    imports=tuple(fixed_file_info_imports),
                    classes=existing_file_info.classes,
                    functions=existing_file_info.functions,
                    constants=existing_file_info.constants,
                )
    return py_file_info_by_module


def for_python_files(
    py_files_digest_contents: DigestContents,
    include_top_level_package: bool,
    ignored_import_names_by_module: Dict[str, Tuple[str, ...]] = {},
) -> PythonPackageHelper:
    # Generate py_file_info_by_module mapping and normalize relative imports
    file_info_by_module: Dict[str, PythonFileInfo] = {}
    for file_content in py_files_digest_contents:
        result_file_info = from_python_file_path(
            file_path=file_content.path,
            file_content=file_content.content,
            module_key=python_utils.generate_relative_module_key(
                py_file_path=file_content.path, include_top_level_package=include_top_level_package
            ),
        )
        file_info_by_module[result_file_info.module_key] = result_file_info
    file_info_by_module = unwind_relative_imports(py_file_info_by_module=file_info_by_module)

    # Generate py_file_info_by_import_star mapping
    file_info_by_import_module_str: Dict[str, Tuple[PythonFileInfo, ...]] = defaultdict(tuple)
    for py_file_info in file_info_by_module.values():
        for py_import in py_file_info.imports:
            file_info_by_import_module_str[py_import.modules_str] = tuple(
                list(file_info_by_import_module_str[py_import.modules_str]) + [py_file_info]
            )
    return PythonPackageHelper(
        include_top_level_package=include_top_level_package,
        py_file_info_by_module=FrozenDict(file_info_by_module),
        py_file_info_by_import_module_str=FrozenDict(file_info_by_import_module_str),
        ignored_import_names_by_module=FrozenDict(ignored_import_names_by_module),
    )


def update_for_python_files(
    py_files_digest_contents: DigestContents, py_package_helper: PythonPackageHelper
) -> PythonPackageHelper:
    # Generate py_file_info_by_module mapping and normalize relative imports
    file_info_by_module: Dict[str, PythonFileInfo] = py_package_helper.py_file_info_by_module
    for file_content in py_files_digest_contents:
        result_file_info = from_python_file_path(
            file_path=file_content.path,
            file_content=file_content.content,
            module_key=python_utils.generate_relative_module_key(
                py_file_path=file_content.path, include_top_level_package=py_package_helper.include_top_level_package
            ),
        )
        file_info_by_module[result_file_info.module_key] = result_file_info
    file_info_by_module = unwind_relative_imports(py_file_info_by_module=file_info_by_module)

    # Generate py_file_info_by_import_star mapping
    file_info_by_import_module_str: Dict[
        str, Tuple[PythonFileInfo, ...]
    ] = py_package_helper.py_file_info_by_import_module_str
    for py_file_info in file_info_by_module.values():
        for py_import in py_file_info.imports:
            [
                py_file_info
                for py_file_info in file_info_by_import_module_str.get(py_import.modules_str, ())
                if py_file_info.path != py_file_info.path
            ]
            file_info_by_import_module_str[py_import.modules_str] = tuple(
                list(file_info_by_import_module_str[py_import.modules_str]) + [py_file_info]
            )
    return PythonPackageHelper(
        include_top_level_package=py_package_helper.include_top_level_package,
        py_file_info_by_module=FrozenDict(file_info_by_module),
        py_file_info_by_import_module_str=FrozenDict(file_info_by_import_module_str),
        ignored_import_names_by_module=file_info_by_module.ignored_import_names_by_module,
    )
