from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple

from pants.engine.fs import DigestContents
from pants.util.frozendict import FrozenDict

from . import utils
from .python_file_info import PythonFileInfo, PythonImport, from_python_file_path


@dataclass(frozen=True)
class PythonPackageHelper:
    include_top_level_package: bool
    python_file_info_by_module: FrozenDict[str, PythonFileInfo]
    python_file_info_by_import_star: FrozenDict[str, Tuple[PythonFileInfo, ...]]
    ignored_import_names_by_module: FrozenDict[str, Tuple[str, ...]]

    def get_python_file_info_from_file_path(self, file_path: str) -> PythonFileInfo:
        module_key = utils.generate_relative_module_key(
            app_python_file_path=file_path, include_top_level_package=self.include_top_level_package
        )
        return self.python_file_info_by_module[module_key]

    def get_transtive_python_files_by_wildcard_import(
        self, source_python_file_info: PythonFileInfo
    ) -> Tuple[PythonFileInfo, ...]:
        return self.python_file_info_by_import_star.get(f"from {source_python_file_info.module_key} import *", [])

    def get_names_used_from_transitive_python_file(
        self, source_py_file: PythonFileInfo, transitive_py_file: PythonFileInfo
    ) -> Tuple[str, ...]:
        names = []
        file_content = source_py_file.file_content_str
        for class_target in transitive_py_file.classes:
            if utils.has_symbol_usage(symbol=class_target.name, file_content=file_content):
                names.append(class_target.name)
        for function_target in transitive_py_file.functions:
            if utils.has_symbol_usage(symbol=function_target.name, file_content=file_content):
                names.append(function_target.name)
        for constant_target in transitive_py_file.constants:
            for src_constant in source_py_file.constants:
                if constant_target.name == src_constant.name:
                    break
            else:
                if utils.has_symbol_usage(symbol=constant_target.name, file_content=file_content):
                    names.append(constant_target.name)

        if transitive_py_file.module_key in self.ignored_import_names_by_module:
            names_to_skip = self.ignored_import_names_by_module[source_py_file.module_key]
            names = set(names) - set(names_to_skip)
        return tuple(names)

    def get_imports_used_from_transitive_python_file(
        self, source_py_file: PythonFileInfo, transitive_py_file: PythonFileInfo
    ) -> Tuple[PythonImport, ...]:
        import_targets = []
        for import_target in transitive_py_file.imports:
            defined_names = import_target.names
            if import_target.modules_str in self.python_file_info_by_module:
                defined_names = self.get_python_file_defined_names_from_import(
                    python_import=import_target, py_file=self.python_file_info_by_module[import_target.modules_str]
                )
            names_used = []
            for name in defined_names:
                if utils.has_symbol_usage(symbol=name, file_content=source_py_file.file_content_str):
                    names_used.append(name)
            if import_target.modules_str in self.ignored_import_names_by_module:
                names_to_skip = self.ignored_import_names_by_module[import_target.modules_str]
                names_used = set(names_used) - set(names_to_skip)
            if names_used:
                import_targets.append(
                    PythonImport(
                        modules=import_target.modules,
                        level=import_target.level,
                        names=tuple(names_used),
                        aliases=(),
                    )
                )
        return tuple(import_targets)

    def get_python_file_defined_names_from_import(
        self, python_import: PythonImport, py_file: PythonFileInfo
    ) -> List[str]:
        defined_names = []
        for name in python_import.names:
            if py_file.has_name(name):
                defined_names.append(name)
        return defined_names

    def update_file_contents(self, updated_python_files_digest_contents: List[Tuple[str, bytes]]) -> None:
        for file_content in updated_python_files_digest_contents:
            file_info = self.get_python_file_info_from_file_path(file_path=file_content.path)
            if file_info is None:
                continue
            updated_dict = dict(self.python_file_info_by_module)
            updated_dict[file_info.module_key] = PythonFileInfo(
                path=file_info.path,
                file_content=file_content.content,
                module_key=file_info.module_key,
                imports=file_info.imports,
                classes=file_info.classes,
                functions=file_info.functions,
                constants=file_info.constants
            )
            self.python_file_info_by_module = FrozenDict(updated_dict)



def unwind_relative_imports(file_target_by_module: Dict[str, PythonFileInfo]) -> Dict[str, PythonFileInfo]:
    for module_key in file_target_by_module:
        for i in range(len(file_target_by_module[module_key].imports)):
            existing_file_info = file_target_by_module[module_key]
            current_import = existing_file_info.imports[i]
            if current_import.is_absolute is False and current_import.modules is not None:
                fixed_file_info_imports = list(file_target_by_module[module_key].imports)
                fixed_file_info_imports[i] = PythonImport(
                    modules=tuple(module_key.split(".")[: (-1 * current_import.level)]) + current_import.modules,
                    level=0,
                    names=current_import.names,
                    aliases=current_import.aliases,
                )
                file_target_by_module[module_key] = PythonFileInfo(
                    path=existing_file_info.path,
                    file_content=existing_file_info.file_content,
                    module_key=existing_file_info.module_key,
                    imports=tuple(fixed_file_info_imports),
                    classes=existing_file_info.classes,
                    functions=existing_file_info.functions,
                    constants=existing_file_info.constants,
                )
    return file_target_by_module


def for_python_files(
    python_files_digest_contents: DigestContents,
    include_top_level_package: bool,
    ignored_import_names_by_module: Dict[str, Tuple[str, ...]] = {},
) -> PythonPackageHelper:
    # Generate file_target_by_module mapping and normalize relative imports
    file_info_by_module: Dict[str, PythonFileInfo] = {}
    for file_content in python_files_digest_contents:
        result_file_info = from_python_file_path(
            file_path=file_content.path,
            file_content=file_content.content,
            module_key=utils.generate_relative_module_key(
                app_python_file_path=file_content.path, include_top_level_package=include_top_level_package
            ),
        )
        file_info_by_module[result_file_info.module_key] = result_file_info
    file_info_by_module = unwind_relative_imports(file_target_by_module=file_info_by_module)

    # Generate file_targets_by_import_star mapping
    file_targets_by_import_star: Dict[str, Tuple[PythonFileInfo, ...]] = defaultdict(tuple)
    for file_target in file_info_by_module.values():
        for import_target in file_target.imports:
            if import_target.is_star_import:
                vals = list(file_targets_by_import_star[import_target.import_str])
                vals.append(file_target)
                file_targets_by_import_star[import_target.import_str] = tuple(vals)
    return PythonPackageHelper(
        include_top_level_package=include_top_level_package,
        python_file_info_by_module=FrozenDict(file_info_by_module),
        python_file_info_by_import_star=FrozenDict(file_targets_by_import_star),
        ignored_import_names_by_module=FrozenDict(ignored_import_names_by_module),
    )
