from dataclasses import dataclass

from pants.engine.rules import rule

from .import_fixer import ImportFixerHandler, PythonFileImportRecommendations
from .python_file_info import PythonFileInfo
from .python_package_helper import PythonPackageHelper


@dataclass(frozen=True)
class PythonFileImportRecommendationsRequest:
    file_path: str
    python_package_helper: PythonPackageHelper

    @property
    def python_file_info(self) -> PythonFileInfo:
        return self.python_package_helper.get_python_file_info_from_file_path(file_path=self.file_path)


@rule(desc="Gets imports * recommendations for a python target")
async def get_file_import_recommendations(
    py_file_import_recommendations_req: PythonFileImportRecommendationsRequest,
) -> PythonFileImportRecommendations:
    return ImportFixerHandler(
        python_package_helper=py_file_import_recommendations_req.python_package_helper
    ).get_python_file_wildcard_import_recommendations(
        python_file_info=py_file_import_recommendations_req.python_file_info
    )
