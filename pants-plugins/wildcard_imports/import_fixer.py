import ast
import re
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from . import import_fixer_utils
from .import_fixer_target_types import FileTarget, ImportTarget, from_python_file_path


class ImportFixerHandler:
    def __init__(self, package_root: str, include_top_level_package: bool) -> None:
        self.package_root = Path(package_root)
        self.include_top_level_package = include_top_level_package

    def fix_targets(self, target_paths: List[str]) -> None:
        file_targets_by_module = self.unwind_relative_imports(
            app_file_targets_by_module=self.get_app_file_targets_by_modules()
        )
        file_targets_patches = []
        for target_path in target_paths:
            module_key = import_fixer_utils.generate_relative_module_key(
                app_python_file_path=target_path, include_top_level_package=self.include_top_level_package
            )
            file_target = file_targets_by_module[module_key]
            for import_target in file_target.imports:
                if import_target.is_star_import:
                    res = self.get_star_import_recommendation(
                        source_file_target=file_target,
                        import_result=import_target,
                        file_targets_by_module=file_targets_by_module,
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

        # Perform import patches for each file target
        for file_target_patch in file_targets_patches:
            self.patch_import(
                source_path=file_target_patch[0],
                import_target=file_target_patch[1],
                replacement_import_targets=file_target_patch[2]
            )

    def get_app_file_targets_by_modules(self) -> Dict[str, FileTarget]:
        file_results = {}
        for file_path in self.get_all_python_files(self.package_root):
            result_file_target = from_python_file_path(
                file_path=file_path,
                module_key=import_fixer_utils.generate_relative_module_key(
                    app_python_file_path=str(file_path), include_top_level_package=self.include_top_level_package
                ),
            )
            file_results[result_file_target.module_key] = result_file_target
        return file_results

    def get_all_python_files(self, root: Path):
        result = []
        for path in root.iterdir():
            if path.is_dir():
                result.extend(self.get_all_python_files(path))
            elif path.is_file() and path.suffix == ".py":
                result.append(path)
        return result

    def get_imports(self, root: ast.Module) -> Iterator[ImportTarget]:
        for node in ast.iter_child_nodes(root):
            # Handle Class and Function AST
            if isinstance(node, ast.ClassDef):
                results = list(self.get_imports(node))
                for result in results:
                    yield result
            elif isinstance(node, ast.FunctionDef):
                results = list(self.get_imports(node))
                for result in results:
                    yield result

            # Check if node is Import node and parse result
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

    def unwind_relative_imports(self, app_file_targets_by_module: Dict[str, FileTarget]) -> Dict[str, FileTarget]:
        for module_key in app_file_targets_by_module:
            for i in range(len(app_file_targets_by_module[module_key].imports)):
                current_import = app_file_targets_by_module[module_key].imports[i]
                if current_import.is_absolute is False and current_import.modules is not None:
                    app_file_targets_by_module[module_key].imports[i] = ImportTarget(
                        modules=module_key.split(".") + current_import.modules,
                        level=0,
                        names=current_import.names,
                        aliases=current_import.aliases,
                    )
        return app_file_targets_by_module

    def get_star_import_recommendation(
        self,
        source_file_target: FileTarget,
        import_result: ImportTarget,
        file_targets_by_module: Dict[str, FileTarget],
        import_recommendations: Optional[List[ImportTarget]] = None,
    ) -> List[ImportTarget]:
        if import_recommendations is None:
            import_recommendations = []
        try:
            transitive_file_target: FileTarget = file_targets_by_module[import_result.modules_str]
        except KeyError:
            return import_recommendations

        # Check usage of direct transitive file target names
        names = transitive_file_target.get_names_used_in_file_target(source_file_target=source_file_target)
        if names:
            import_recommendations.append(
                ImportTarget(modules=transitive_file_target.module_key.split("."), level=0, names=names, aliases=[])
            )

        # Get usage of imports names from transitive file target
        import_recommendations.extend(
            transitive_file_target.get_imports_used_in_file_target(source_file_target=source_file_target)
        )

        # Recurse on transitive 'import *' to find nested symbol usages
        for transitive_import_target in transitive_file_target.imports:
            if transitive_import_target.is_star_import:
                return self.get_star_import_recommendation(
                    source_file_target=source_file_target,
                    import_result=transitive_import_target,
                    file_targets_by_module=file_targets_by_module,
                    import_recommendations=import_recommendations,
                )
        return import_recommendations

    def patch_import(
        self, source_path: Path, import_target: ImportTarget, replacement_import_targets: List[ImportTarget]
    ) -> None:
        regex_str = import_target.import_str.replace("*", "\*")  # noqa: W605
        replacement_import_strs = set()
        for replacement_import_target in replacement_import_targets:
            replacement_import_strs.add(replacement_import_target.import_str)
        contents = re.sub(regex_str, "\n".join(replacement_import_strs), source_path.read_text())
        source_path.write_text(contents)
