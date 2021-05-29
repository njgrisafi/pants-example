from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Tuple

from pants.engine.fs import DigestContents

from . import utils
from .python_file_info import PythonFileInfo, PythonImport, from_python_file_path


@dataclass(frozen=True)
class PythonPackageHelper:
    include_top_level_package: bool
    python_file_info_by_module: Dict[str, PythonFileInfo]
    python_file_info_by_import_star: Dict[str, Tuple[PythonFileInfo]]

    def get_python_file_info_from_file_path(self, file_path: str) -> PythonFileInfo:
        module_key = utils.generate_relative_module_key(
            app_python_file_path=file_path, include_top_level_package=self.include_top_level_package
        )
        return self.python_file_info_by_module[module_key]

    def get_transtive_python_files_by_wildcard_import(
        self, source_python_file_info: PythonFileInfo
    ) -> Tuple[PythonFileInfo]:
        return self.python_file_info_by_import_star.get(f"from {source_python_file_info.module_key} import *", [])


def unwind_relative_imports(file_target_by_module: Dict[str, PythonFileInfo]) -> Dict[str, PythonFileInfo]:
    for module_key in file_target_by_module:
        for i in range(len(file_target_by_module[module_key].imports)):
            current_import = file_target_by_module[module_key].imports[i]
            if current_import.is_absolute is False and current_import.modules is not None:
                file_target_by_module[module_key].imports[i] = PythonImport(
                    modules=module_key.split(".") + current_import.modules,
                    level=0,
                    names=current_import.names,
                    aliases=current_import.aliases,
                )
    return file_target_by_module


def for_python_files(
    python_files_digest_contents: DigestContents, include_top_level_package: bool
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
    file_targets_by_import_star: Dict[str, Tuple[PythonFileInfo]] = defaultdict(tuple)
    for file_target in file_info_by_module.values():
        for import_target in file_target.imports:
            if import_target.is_star_import:
                vals = list(file_targets_by_import_star[import_target.import_str])
                vals.append(file_target)
                file_targets_by_import_star[import_target.import_str] = tuple(vals)
    return PythonPackageHelper(
        include_top_level_package=include_top_level_package,
        python_file_info_by_module=file_info_by_module,
        python_file_info_by_import_star=file_targets_by_import_star,
    )
