from dataclasses import dataclass
from typing import Tuple

from import_fixer.python_connect.python_file_info import PythonFileInfo, PythonImport
from import_fixer.python_connect.python_package_helper import PythonPackageHelper


@dataclass(frozen=True)
class PythonFileIndirectImportRecommendationsRequest:
    py_file_info: PythonFileInfo
    py_package_helper: PythonPackageHelper


@dataclass(frozen=True)
class PythonFileIsNameDefinedRequest:
    py_file_info: PythonFileInfo
    source_import: PythonImport
    name: str


@dataclass(frozen=True)
class PythonFileIsNameDefinedResponse:
    py_file_info: PythonFileInfo
    source_import: PythonImport
    name: str
    is_defined: bool


@dataclass(frozen=True)
class PythonPackageImportsForNameRequest:
    py_package_helper: PythonPackageHelper
    name: str


@dataclass(frozen=True)
class PythonPackageImportsForNameResponse:
    name: str
    py_imports: Tuple[PythonImport, ...]
