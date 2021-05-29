import re
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from pants.engine.fs import FileContent

from . import utils
from .python_file_info import PythonFileInfo, PythonImport
from .python_package_helper import PythonPackageHelper


@dataclass(frozen=True)
class WildcardImportRecommendation:
    wildcard_import: PythonImport
    recommendations: Tuple[PythonImport]


@dataclass(frozen=True)
class PythonFileImportRecommendations:
    python_file_info: PythonFileInfo
    wildcard_import_recommendations: Tuple[WildcardImportRecommendation]
    transitive_import_recs: Tuple["PythonFileImportRecommendations"]

    @property
    def fixed_file_content(self) -> FileContent:
        content = self.python_file_info.file_content_str
        for import_rec in self.wildcard_import_recommendations:
            regex_str = import_rec.wildcard_import.import_str.replace("*", "\*")  # noqa: W605
            replacement_import_strs = set()
            for replacement_import_target in import_rec.recommendations:
                replacement_import_strs.add(replacement_import_target.import_str)
            content = re.sub(regex_str, "\n".join(replacement_import_strs), content)
        return FileContent(
            path=self.python_file_info.path,
            content=content.encode()
        )


class ImportFixerHandler:
    def __init__(self, python_package_helper: PythonPackageHelper) -> None:
        self.python_package_helper = python_package_helper

    def get_python_file_wildcard_import_recommendations(
        self, python_file_info: PythonFileInfo
    ) -> PythonFileImportRecommendations:
        return PythonFileImportRecommendations(
            python_file_info=python_file_info,
            wildcard_import_recommendations=tuple(
                self.generate_python_wildcard_import_recommendations(python_file_info=python_file_info)
            ),
            transitive_import_recs=tuple(
                self.generate_transitive_python_file_import_recommendations(python_file_info=python_file_info)
            ),
        )

    def generate_python_wildcard_import_recommendations(
        self, python_file_info: PythonFileInfo
    ) -> Iterable[WildcardImportRecommendation]:
        for python_import in python_file_info.imports:
            if python_import.is_star_import:
                recs = self.get_star_import_recommendation(
                    source_python_file_info=python_file_info,
                    python_wildcard_import=python_import,
                )
                if len(recs) == 0:
                    continue
                yield WildcardImportRecommendation(wildcard_import=python_import, recommendations=recs)

    def generate_transitive_python_file_import_recommendations(
        self, python_file_info: PythonFileInfo
    ) -> Iterable[PythonFileImportRecommendations]:
        # Update python files that import the current python file via a wildcard import
        for transitive_python_file in self.python_package_helper.get_transtive_python_files_by_wildcard_import(
            source_python_file_info=python_file_info
        ):
            star_import_target = PythonImport(
                modules=tuple(python_file_info.module_key.split(".")), level=0, names=("*",), aliases=()
            )
            recs = self.get_star_import_recommendation(
                source_python_file_info=transitive_python_file,
                python_wildcard_import=star_import_target,
            )
            if len(recs) == 0:
                continue
            yield PythonFileImportRecommendations(
                python_file_info=transitive_python_file,
                wildcard_import_recommendations=(
                    WildcardImportRecommendation(wildcard_import=star_import_target, recommendations=recs),
                ),
                transitive_import_recs=(),
            )

    def get_star_import_recommendation(
        self,
        source_python_file_info: PythonFileInfo,
        python_wildcard_import: PythonImport,
    ) -> Tuple[PythonImport]:
        visited = []
        import_recommendations: List[PythonImport] = []
        stack = [python_wildcard_import]
        while stack:
            import_target = stack.pop()
            if import_target.modules_str in visited:
                continue
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
    ) -> Tuple[PythonImport]:
        import_recommendations = []

        # Check usage of direct transitive python file names
        names = transitive_python_file_info.get_names_used_by_file_target(source_file_target=source_python_file_info)
        if names:
            import_recommendations.append(
                PythonImport(
                    modules=tuple(transitive_python_file_info.module_key.split(".")), level=0, names=names, aliases=()
                )
            )

        # Get usage of imports names from transitive python file
        import_recommendations.extend(
            transitive_python_file_info.get_imports_used_by_file_target(source_file_target=source_python_file_info)
        )
        return import_recommendations

    def get_submodule_import_recommendations_for_python_file(
        self, source_python_file_info: PythonFileInfo, module_python_import: PythonImport
    ) -> Tuple[PythonImport]:
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

    def get_module_directory_imports_recommendations_for_python_file(
        self, source_python_file_info: PythonFileInfo, module_python_import: PythonImport
    ) -> List[PythonImport]:
        module_directory_import_targets = []
        for module_key, python_file_info in self.python_package_helper.python_file_info_by_module.items():
            symbol = python_file_info.module_key.split(".")[-1]
            if module_python_import.modules_str in module_key and utils.has_symbol_usage(
                symbol=symbol, file_content=source_python_file_info.file_content_str
            ):
                module_directory_import_targets.append(
                    PythonImport(modules=module_python_import.modules, level=0, names=(symbol,), aliases=())
                )
        return module_directory_import_targets
