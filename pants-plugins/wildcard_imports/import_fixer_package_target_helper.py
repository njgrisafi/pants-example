from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from . import import_fixer_utils
from .import_fixer_python_target_types import FileTarget, ImportTarget, from_python_file_path


@dataclass
class PackageTargetHelper:
    include_top_level_package: bool
    file_target_by_module: Dict[str, FileTarget]
    file_targets_by_import_star: Dict[str, List[FileTarget]]

    def get_file_target_from_python_file_path(self, file_path: str) -> FileTarget:
        module_key = import_fixer_utils.generate_relative_module_key(
            app_python_file_path=file_path, include_top_level_package=self.include_top_level_package
        )
        return self.file_target_by_module[module_key]

    def get_module_star_import_file_targets(self, file_target: FileTarget) -> List[FileTarget]:
        return self.file_targets_by_import_star.get(f"from {file_target.module_key} import *", [])


def unwind_relative_imports(file_target_by_module: Dict[str, FileTarget]) -> Dict[str, FileTarget]:
    for module_key in file_target_by_module:
        for i in range(len(file_target_by_module[module_key].imports)):
            current_import = file_target_by_module[module_key].imports[i]
            if current_import.is_absolute is False and current_import.modules is not None:
                file_target_by_module[module_key].imports[i] = ImportTarget(
                    modules=module_key.split(".") + current_import.modules,
                    level=0,
                    names=current_import.names,
                    aliases=current_import.aliases,
                )
    return file_target_by_module


def from_package_root(package_root: Path, include_top_level_package: bool) -> PackageTargetHelper:
    # Generate file_target_by_module mapping and normalize relative imports
    file_target_by_module: Dict[str, FileTarget] = {}
    for file_path in import_fixer_utils.get_all_python_files(package_root):
        result_file_target = from_python_file_path(
            file_path=file_path,
            module_key=import_fixer_utils.generate_relative_module_key(
                app_python_file_path=str(file_path), include_top_level_package=include_top_level_package
            ),
        )
        file_target_by_module[result_file_target.module_key] = result_file_target
    file_target_by_module = unwind_relative_imports(file_target_by_module=file_target_by_module)

    # Generate file_targets_by_import_star mapping
    file_targets_by_import_star: Dict[str, List[FileTarget]] = defaultdict(list)
    for file_target in file_target_by_module.values():
        for import_target in file_target.imports:
            if import_target.is_star_import:
                file_targets_by_import_star[import_target.import_str].append(file_target)
    return PackageTargetHelper(
        include_top_level_package=include_top_level_package,
        file_target_by_module=file_target_by_module,
        file_targets_by_import_star=file_targets_by_import_star,
    )
