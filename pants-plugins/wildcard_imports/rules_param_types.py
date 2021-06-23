from dataclasses import dataclass
from typing import Optional, Tuple

from wildcard_imports.import_fixer.python_file_info import PythonFileInfo, PythonImport
from wildcard_imports.import_fixer.python_package_helper import PythonPackageHelper


@dataclass(frozen=True)
class PythonFileImportRecommendationsRequest:
    py_file_info: PythonFileInfo
    py_package_helper: PythonPackageHelper


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
    py_file_info: PythonFileInfo
    transitive_py_file_info: PythonFileInfo
    py_package_helper: PythonPackageHelper

    @property
    def py_import(self) -> PythonImport:
        for py_import in self.transitive_py_file_info.imports:
            if self.py_file_info.module_key == py_import.modules_str:
                return py_import
        raise Exception("Import not found!")


@dataclass(frozen=True)
class PythonFileTransitiveNamesRequest:
    py_file_info: PythonFileInfo
    transitive_py_file_info: PythonFileInfo
    py_package_helper: PythonPackageHelper


@dataclass(frozen=True)
class PythonFileTransitiveNamesResponse:
    names: Tuple[str, ...]


@dataclass(frozen=True)
class PythonFileTransitiveImportsRequest:
    py_file_info: PythonFileInfo
    transitive_py_file_info: PythonFileInfo
    py_package_helper: PythonPackageHelper


@dataclass(frozen=True)
class PythonFileTransitiveImportsResponse:
    py_imports: Tuple[PythonImport, ...]


@dataclass(frozen=True)
class PythonFileImportDefinedNamesRequest:
    py_file_info: PythonFileInfo
    py_import: PythonImport


@dataclass(frozen=True)
class PythonFileImportDefinedNamesResponse:
    defined_names: Tuple[str, ...]


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
