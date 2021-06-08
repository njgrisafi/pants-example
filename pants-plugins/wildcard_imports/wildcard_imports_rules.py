from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from pants.engine.rules import Get, MultiGet, Rule, collect_rules, rule
from wildcard_imports.import_fixer import utils
from wildcard_imports.import_fixer.import_fixer_handler import (
    ImportFixerHandler,
    PythonFileImportRecommendations,
    PythonImportRecommendation,
)
from wildcard_imports.import_fixer.python_file_info import PythonFileInfo, PythonImport
from wildcard_imports.import_fixer.python_package_helper import PythonPackageHelper


@dataclass(frozen=True)
class PythonFileImportRecommendationsRequest:
    file_path: str
    py_package_helper: PythonPackageHelper

    @property
    def py_file_info(self) -> PythonFileInfo:
        return self.py_package_helper.get_python_file_info_from_file_path(file_path=self.file_path)


@dataclass(frozen=True)
class PythonFileWildcardImportRecommendationsRequest(PythonFileImportRecommendationsRequest):
    ...


@dataclass(frozen=True)
class PythonFileDuplicateImportRecommendationsRequest(PythonFileImportRecommendationsRequest):
    ...


@dataclass(frozen=True)
class PythonFileMissingImportRecommendationsRequest(PythonFileImportRecommendationsRequest):
    ...


@dataclass(frozen=True)
class WildcardImportRecommendationsRequest:
    source_py_file_info: PythonFileInfo
    wildcard_import: PythonImport
    py_package_helper: PythonPackageHelper


@dataclass(frozen=True)
class PythonTransitiveFileImportRecommendationsRequest:
    transitive_py_file_info: PythonFileInfo
    py_file_import_reccomendations: PythonFileImportRecommendations
    py_package_helper: PythonPackageHelper

    @property
    def py_file_info(self) -> PythonFileInfo:
        return self.py_file_import_reccomendations.py_file_info


@dataclass(frozen=True)
class DuplicateImportRecommendationsRequest:
    py_file_info: PythonFileInfo
    duplicate_imports: Tuple[PythonImport, ...]
    duplicate_name: str
    py_package_helper: PythonPackageHelper


@dataclass(frozen=True)
class MissingImportRecommendationRequest:
    missing_name: str
    py_package_helper: PythonPackageHelper


@dataclass(frozen=True)
class FixedWildcardImport:
    wildcard_import: PythonImport
    replacement_imports: Tuple[PythonImport, ...]


@rule(desc="Gets all wildcard import recommendations for a python file")
async def get_file_import_recommendations(
    py_file_import_recommendations_req: PythonFileWildcardImportRecommendationsRequest,
) -> PythonFileImportRecommendations:
    get_commands: List[Get] = []
    for python_import in py_file_import_recommendations_req.py_file_info.imports:
        if python_import.is_wildcard_import:
            get_commands.append(
                Get(
                    PythonImportRecommendation,
                    WildcardImportRecommendationsRequest,
                    WildcardImportRecommendationsRequest(
                        source_py_file_info=py_file_import_recommendations_req.py_file_info,
                        wildcard_import=python_import,
                        py_package_helper=py_file_import_recommendations_req.py_package_helper,
                    ),
                )
            )
    import_recommendations = await MultiGet(get_commands)
    return PythonFileImportRecommendations(
        py_file_info=py_file_import_recommendations_req.py_file_info,
        import_recommendations=import_recommendations,
    )


@rule(desc="Gets a single wildcard import recommendation for a python file")
async def get_wildcard_import_recommendation(
    wildcard_import_rec_req: WildcardImportRecommendationsRequest,
) -> PythonImportRecommendation:
    recs = ImportFixerHandler(
        py_package_helper=wildcard_import_rec_req.py_package_helper
    ).get_wildcard_import_recommendation(
        source_py_file_info=wildcard_import_rec_req.source_py_file_info,
        python_wildcard_import=wildcard_import_rec_req.wildcard_import,
    )
    return PythonImportRecommendation(source_import=wildcard_import_rec_req.wildcard_import, recommendations=recs)


@rule(desc="Gets transitive wildcard import recommendations for a python import recommendation")
async def get_file_transitive_import_recommendations(
    py_transitive_file_import_rec_req: PythonTransitiveFileImportRecommendationsRequest,
) -> PythonFileImportRecommendations:
    return ImportFixerHandler(
        py_package_helper=py_transitive_file_import_rec_req.py_package_helper
    ).get_transitive_python_file_import_recommendations(
        py_file_info=py_transitive_file_import_rec_req.py_file_info,
        transitive_py_file_info=py_transitive_file_import_rec_req.transitive_py_file_info,
    )


@rule(desc="Gets duplicate import recommendations for a python file")
async def get_file_duplicate_import_recommendations(
    py_file_dup_import_rec_req: PythonFileDuplicateImportRecommendationsRequest,
) -> PythonFileImportRecommendations:
    imports_by_names: Dict[str, List[PythonImport]] = defaultdict(list)
    for python_import in py_file_dup_import_rec_req.py_file_info.imports:
        for name in python_import.names:
            imports_by_names[name].append(python_import)

    # Get all duplciate import names
    duplicate_import_by_names: Dict[str, List[PythonImport]] = defaultdict(list)
    for name, python_imports in imports_by_names.items():
        if len(python_imports) > 1:
            duplicate_import_by_names[name] = python_imports

    get_commands: List[Get] = []
    for name, python_imports in duplicate_import_by_names.items():
        get_commands.append(
            Get(
                PythonFileImportRecommendations,
                DuplicateImportRecommendationsRequest,
                DuplicateImportRecommendationsRequest(
                    py_file_info=py_file_dup_import_rec_req.py_file_info,
                    duplicate_imports=tuple(python_imports),
                    duplicate_name=name,
                    py_package_helper=py_file_dup_import_rec_req.py_package_helper,
                ),
            )
        )
    dup_file_import_recs: Tuple[PythonFileImportRecommendations, ...] = await MultiGet(get_commands)

    merged_recommendations = ()
    for file_import_rec in dup_file_import_recs:
        merged_recommendations = tuple(set(list(merged_recommendations) + list(file_import_rec.import_recommendations)))
    return PythonFileImportRecommendations(
        py_file_info=py_file_dup_import_rec_req.py_file_info, import_recommendations=merged_recommendations
    )


@rule(desc="Gets duplicate import recommendations")
async def get_duplicate_import_recommendations(
    dup_import_rec_req: DuplicateImportRecommendationsRequest,
) -> PythonFileImportRecommendations:
    recs = ImportFixerHandler(
        py_package_helper=dup_import_rec_req.py_package_helper
    ).get_file_duplicate_import_recommendations(
        duplicate_imports=dup_import_rec_req.duplicate_imports, duplicate_name=dup_import_rec_req.duplicate_name
    )
    return PythonFileImportRecommendations(
        py_file_info=dup_import_rec_req.py_file_info, import_recommendations=recs
    )


@rule(desc="Gets missing import recommendations")
async def get_file_missing_import_recommendations(
    py_file_missing_import_rec_req: PythonFileMissingImportRecommendationsRequest,
) -> PythonFileImportRecommendations:
    missing_names = utils.get_missing_import_names(
        file_content=py_file_missing_import_rec_req.py_file_info.file_content
    )
    get_commands: List[Get] = []
    for name in missing_names:
        get_commands.append(
            Get(
                PythonImportRecommendation,
                MissingImportRecommendationRequest,
                MissingImportRecommendationRequest(
                    missing_name=name,
                    py_package_helper=py_file_missing_import_rec_req.py_package_helper,
                ),
            )
        )
    missing_import_recs: Tuple[PythonImportRecommendation, ...] = await MultiGet(get_commands)
    return PythonFileImportRecommendations(
        py_file_info=py_file_missing_import_rec_req.py_file_info, import_recommendations=missing_import_recs
    )


@rule(desc="Gets missing import recommendations")
async def get_missing_import_recommendation(
    missing_import_rec_req: MissingImportRecommendationRequest,
) -> PythonImportRecommendation:
    return ImportFixerHandler(
        py_package_helper=missing_import_rec_req.py_package_helper
    ).get_missing_import_recommendation(missing_name=missing_import_rec_req.missing_name)


def rules() -> Iterable[Rule]:
    return collect_rules()
