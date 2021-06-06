import re
from dataclasses import dataclass
from typing import List, Tuple

from pants.engine.fs import FileContent

from . import utils
from .python_file_info import PythonFileInfo, PythonImport
from .python_package_helper import PythonPackageHelper


@dataclass(frozen=True)
class PythonImportRecommendation:
    source_import: PythonImport
    recommendations: Tuple[PythonImport, ...]


@dataclass(frozen=True)
class PythonFileImportRecommendations:
    python_file_info: PythonFileInfo
    import_recommendations: Tuple[PythonImportRecommendation, ...]

    @property
    def fixed_file_content(self) -> FileContent:
        content = self.python_file_info.file_content_str
        for import_rec in self.import_recommendations:
            regex_str = import_rec.source_import.import_str.replace("*", "\*")  # noqa: W605
            if len(import_rec.recommendations) == 0:
                content = re.sub(regex_str, "", content)
            else:
                replacement_import_strs = set(
                    [replacement_import_target.import_str for replacement_import_target in import_rec.recommendations]
                )
                content = re.sub(regex_str, "\n".join(replacement_import_strs), content)
        return FileContent(path=self.python_file_info.path, content=content.encode())


class ImportFixerHandler:
    def __init__(self, python_package_helper: PythonPackageHelper) -> None:
        self.python_package_helper = python_package_helper

    def get_transitive_python_file_import_recommendations(
        self, python_file_info: PythonFileInfo, transitive_python_file: PythonFileInfo
    ) -> PythonFileImportRecommendations:
        # Update python files that import the current python file via a wildcard import
        star_import_target = PythonImport(
            modules=tuple(python_file_info.module_key.split(".")), level=0, names=("*",), aliases=()
        )
        recs = self.get_star_import_recommendation(
            source_python_file_info=transitive_python_file,
            python_wildcard_import=star_import_target,
        )
        return PythonFileImportRecommendations(
            python_file_info=transitive_python_file,
            import_recommendations=(
                PythonImportRecommendation(source_import=star_import_target, recommendations=recs),
            ),
        )

    def get_star_import_recommendation(
        self,
        source_python_file_info: PythonFileInfo,
        python_wildcard_import: PythonImport,
    ) -> Tuple[PythonImport, ...]:
        visited = []
        import_recommendations: List[PythonImport] = []
        stack = [python_wildcard_import]
        while stack:
            import_target = stack.pop()
            if import_target.modules_str in visited:
                continue
            print(source_python_file_info, import_target.modules_str)
            visited.append(import_target.modules_str)
            try:
                transitive_python_file_info = self.python_package_helper.python_file_info_by_module[
                    import_target.modules_str
                ]
                import_recommendations.extend(
                    self.get_transitive_import_recommendations(
                        source_python_file_info=source_python_file_info,
                        transitive_python_file_info=transitive_python_file_info,
                    )
                )

                if transitive_python_file_info.is_module:
                    raise KeyError("Trigger submodule check")
            except KeyError:
                # Check for submodule direct usages in source python file
                import_recommendations.extend(
                    self.get_submodule_import_recommendations_for_python_file(
                        source_python_file_info=source_python_file_info,
                        module_python_import=import_target,
                    )
                )

                # Queue all submodules for transitive checks
                stack.extend(self.get_submodule_transitive_imports(module_python_import=import_target))
                continue

            # iterate on transitive 'import *' to find nested symbol usages
            for transitive_import_target in transitive_python_file_info.imports:
                if transitive_import_target.is_star_import:
                    stack.append(transitive_import_target)
        return tuple(import_recommendations)

    def get_transitive_import_recommendations(
        self, source_python_file_info: PythonFileInfo, transitive_python_file_info: PythonFileInfo
    ) -> Tuple[PythonImport, ...]:
        import_recommendations = []

        # Check usage of direct transitive python file names
        names = self.python_package_helper.get_names_used_from_transitive_python_file(
            source_py_file=source_python_file_info, transitive_py_file=transitive_python_file_info
        )
        if names:
            import_recommendations.append(
                PythonImport(
                    modules=tuple(transitive_python_file_info.module_key.split(".")), level=0, names=names, aliases=()
                )
            )

        # Get usage of imports names from transitive python file
        import_recommendations.extend(
            self.python_package_helper.get_imports_used_from_transitive_python_file(
                source_py_file=source_python_file_info, transitive_py_file=transitive_python_file_info
            )
        )
        return import_recommendations

    def get_submodule_import_recommendations_for_python_file(
        self, source_python_file_info: PythonFileInfo, module_python_import: PythonImport
    ) -> Tuple[PythonImport, ...]:
        module_directory_python_imports = []
        for module_key, python_file_info in self.python_package_helper.python_file_info_by_module.items():
            symbol = python_file_info.module_key.split(".")[-1]
            if module_python_import.modules_str in module_key and utils.has_symbol_usage(
                symbol=symbol, file_content=source_python_file_info.file_content_str
            ):
                module_directory_python_imports.append(
                    PythonImport(modules=module_python_import.modules, level=0, names=(symbol,), aliases=())
                )
        return module_directory_python_imports

    def get_submodule_transitive_imports(self, module_python_import: PythonImport) -> List[PythonImport]:
        submodule_python_imports = []
        for module_key in self.python_package_helper.python_file_info_by_module:
            if module_python_import.modules_str in module_key:
                submodule_python_imports.append(
                    PythonImport(modules=tuple(module_key.split(".")), level=0, names=("*",), aliases=())
                )
        return submodule_python_imports

    def get_file_duplicate_import_recommendations(
        self, duplicate_imports: Tuple[PythonImport, ...], duplicate_name: str
    ) -> Tuple[PythonImportRecommendation, ...]:
        direct_name_definitions: List[PythonImport] = []
        for duplicate_import in duplicate_imports:
            if (
                f"{duplicate_import.modules_str}.{duplicate_name}"
                in self.python_package_helper.python_file_info_by_module
            ):
                direct_name_definitions.append(duplicate_import)
            elif duplicate_import.modules_str in self.python_package_helper.python_file_info_by_module:
                file_info = self.python_package_helper.python_file_info_by_module[duplicate_import.modules_str]
                if file_info.has_name(name=duplicate_name):
                    direct_name_definitions.append(duplicate_import)
            else:
                direct_name_definitions.append(duplicate_import)
        non_direct_import_definitions = tuple(list(set(duplicate_imports) - set(direct_name_definitions)))
        import_recommendations = []
        for non_direct_import in non_direct_import_definitions:
            updated_names = tuple(set(non_direct_import.names) - {duplicate_name})
            import_recommendations.append(
                PythonImportRecommendation(
                    source_import=non_direct_import,
                    recommendations=(
                        PythonImport(
                            modules=non_direct_import.modules,
                            level=non_direct_import.level,
                            names=updated_names,
                            aliases=non_direct_import.aliases,
                        ),
                    )
                    if updated_names
                    else (),
                )
            )
        return tuple(import_recommendations)
