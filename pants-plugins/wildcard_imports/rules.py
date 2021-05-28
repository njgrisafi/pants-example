from pants.engine.rules import rule

from .import_fixer import ImportFixerHandler, PythonFileImportRecommendations
from .python_file_info import PythonFileInfo
from .python_package_helper import PythonPackageHelper


@rule(desc="Gets imports * recommendations for a python target")
async def get_file_import_recommendations(
    python_file_info: PythonFileInfo, python_package_helper: PythonPackageHelper
) -> PythonFileImportRecommendations:
    return ImportFixerHandler(
        python_package_helper=python_package_helper
    ).get_python_file_wildcard_import_recommendations(python_file_info=python_file_info)
