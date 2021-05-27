import re
from pathlib import Path
from typing import List, Optional

from . import import_fixer_utils
from .import_fixer_package_target_helper import from_package_root
from .import_fixer_python_target_types import FileTarget, ImportTarget


class ImportFixerHandler:
    def __init__(self, package_root: str, include_top_level_package: bool) -> None:
        self.package_root = Path(package_root)
        self.package_helper = from_package_root(
            package_root=self.package_root, include_top_level_package=include_top_level_package
        )

    def fix_targets(self, target_paths: List[str]) -> None:
        file_targets_patches = []
        file_targets_to_fix: List[FileTarget] = []

        # Get all file targets to fix
        for target_path in target_paths:
            file_targets_to_fix.append(self.package_helper.get_file_target_from_python_file_path(file_path=target_path))

        # Fix file targets
        file_paths_seen = []
        for file_target in file_targets_to_fix:
            if file_target.path in file_paths_seen:
                continue
            file_paths_seen.append(file_target.path)
            for import_target in file_target.imports:
                if import_target.is_star_import:
                    res = self.get_star_import_recommendation(
                        source_file_target=file_target,
                        import_target=import_target,
                    )
                    if len(res) == 0:
                        continue
                    file_targets_patches.append(
                        (
                            Path(file_target.path),
                            import_target,
                            res,
                        )
                    )

            # Update targets that wildcard import the current file targets
            for transitive_file_target in self.package_helper.get_module_star_import_file_targets(
                file_target=file_target
            ):
                star_import_target = ImportTarget(
                    modules=file_target.module_key.split("."), level=0, names=["*"], aliases=[]
                )
                res = self.get_star_import_recommendation(
                    source_file_target=transitive_file_target,
                    import_target=star_import_target,
                )
                if len(res) == 0:
                    continue
                file_targets_patches.append(
                    (
                        Path(transitive_file_target.path),
                        star_import_target,
                        res,
                    )
                )

        # Perform import patches for each file target
        for file_target_patch in file_targets_patches:
            self.patch_import(
                source_path=file_target_patch[0],
                import_target=file_target_patch[1],
                replacement_import_targets=file_target_patch[2],
            )

    def get_star_import_recommendation(
        self,
        source_file_target: FileTarget,
        import_target: ImportTarget,
        import_recommendations: Optional[List[ImportTarget]] = None,
    ) -> List[ImportTarget]:
        if import_recommendations is None:
            import_recommendations = []
        try:
            transitive_file_target = self.package_helper.file_target_by_module[import_target.modules_str]
        except KeyError:
            # Check for submodule usages
            import_recommendations.extend(
                self.get_module_directory_import_targets_for_file_target(
                    source_file_target=source_file_target,
                    import_target=import_target,
                )
            )
            return import_recommendations

        # Check usage of direct transitive file target names
        names = transitive_file_target.get_names_used_by_file_target(source_file_target=source_file_target)
        if names:
            import_recommendations.append(
                ImportTarget(modules=transitive_file_target.module_key.split("."), level=0, names=names, aliases=[])
            )

        # Get usage of imports names from transitive file target
        import_recommendations.extend(
            transitive_file_target.get_imports_used_by_file_target(source_file_target=source_file_target)
        )

        # Recurse on transitive 'import *' to find nested symbol usages
        for transitive_import_target in transitive_file_target.imports:
            if transitive_import_target.is_star_import:
                import_recommendations.extend(
                    self.get_star_import_recommendation(
                        source_file_target=source_file_target,
                        import_target=transitive_import_target,
                        import_recommendations=import_recommendations,
                    )
                )
        return import_recommendations

    def get_module_directory_import_targets_for_file_target(
        self, source_file_target: FileTarget, import_target: ImportTarget
    ) -> List[ImportTarget]:
        module_directory_import_targets = []
        for module_key, file_target in self.package_helper.file_target_by_module.items():
            symbol = file_target.module_key.split(".")[-1]
            if import_target.modules_str in module_key and import_fixer_utils.has_symbol_usage(
                symbol=symbol, file_content=source_file_target.file_content_str
            ):
                module_directory_import_targets.append(
                    ImportTarget(modules=import_target.modules, level=0, names=[symbol], aliases=[])
                )
        return module_directory_import_targets

    def patch_import(
        self, source_path: Path, import_target: ImportTarget, replacement_import_targets: List[ImportTarget]
    ) -> None:
        regex_str = import_target.import_str.replace("*", "\*")  # noqa: W605
        replacement_import_strs = set()
        for replacement_import_target in replacement_import_targets:
            replacement_import_strs.add(replacement_import_target.import_str)
        contents = re.sub(regex_str, "\n".join(replacement_import_strs), source_path.read_text())
        source_path.write_text(contents)
