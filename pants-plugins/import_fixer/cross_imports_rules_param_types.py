import json
from dataclasses import dataclass
from typing import Dict, Tuple

from import_fixer.python_connect.python_file_info import PythonFileInfo
from import_fixer.python_connect.python_package_helper import PythonPackageHelper
from pants.util.frozendict import FrozenDict


@dataclass(frozen=True)
class PythonFileCrossImportStatsResponse:
    py_file_info: PythonFileInfo
    cross_imports: FrozenDict[str, int]


@dataclass(frozen=True)
class PythonPackageCrossImportStatsRequest:
    py_package_helper: PythonPackageHelper


@dataclass(frozen=True)
class PythonPackageCrossImportStatsResponse:
    cross_imports: Tuple[PythonFileCrossImportStatsResponse, ...]

    @property
    def to_dict(self) -> Dict[str, dict]:
        result = {}
        for cross_import in self.cross_imports:
            result[cross_import.py_file_info.module_key] = dict(cross_import.cross_imports)
        return result

    @property
    def to_json_str(self) -> str:
        return json.dumps(self.to_dict)


@dataclass(frozen=True)
class PythonFileCrossImportStatsRequest:
    py_file_info: PythonFileInfo
    py_package_helper: PythonPackageHelper
