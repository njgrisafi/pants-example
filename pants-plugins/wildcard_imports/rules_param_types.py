from dataclasses import dataclass
from typing import Tuple

from wildcard_imports.import_fixer.python_file_import_recs import PythonFileImportRecommendations
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
class PythonFileTransitiveImportRecommendationsRequest:
    transitive_py_file_info: PythonFileInfo
    py_file_import_reccomendations: PythonFileImportRecommendations
    py_package_helper: PythonPackageHelper

    @property
    def py_file_info(self) -> PythonFileInfo:
        return self.py_file_import_reccomendations.py_file_info


@dataclass(frozen=True)
class TransitiveImportRecommendationsRequest:
    py_file_info: PythonFileInfo
    transitive_py_file_info: PythonFileInfo
    py_package_helper: PythonPackageHelper


@dataclass(frozen=True)
class TransitiveImportRecommendationsResponse:
    transitive_imports: Tuple[PythonImport, ...]


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


@dataclass(frozen=True)
class PythonFileSubmoduleImportRecommendationsRequest:
    py_file_info: PythonFileInfo
    module_py_import: PythonImport
    py_package_helper: PythonPackageHelper


@dataclass(frozen=True)
class PythonFileSubmoduleImportRecommendationsResponse:
    submodule_py_imports: Tuple[PythonImport, ...]


@dataclass(frozen=True)
class SubmoduleTansitiveWildcardImportsRequest:
    module_py_import: PythonImport
    py_package_helper: PythonPackageHelper


@dataclass(frozen=True)
class SubmoduleTransitiveWildcardImportsResponse:
    submodule_transitive_py_imports: Tuple[PythonImport, ...]
