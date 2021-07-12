from typing import Iterable, List, Tuple

from import_fixer.indirect_imports_rules_param_types import (
    PythonFileIndirectImportRecommendationsRequest,
    PythonFileIsNameDefinedRequest,
    PythonFileIsNameDefinedResponse,
    PythonPackageImportsForNameRequest,
    PythonPackageImportsForNameResponse,
)
from import_fixer.python_connect import python_utils
from import_fixer.python_connect.python_file_import_recs import (
    PythonFileImportRecommendations,
    PythonImportRecommendation,
)
from import_fixer.python_connect.python_file_info import PythonImport
from pants.engine.rules import Get, MultiGet, Rule, collect_rules, rule


@rule(desc="Get all indirect import recommendations for a python file")
async def get_file_indirect_import_recommendations(
    py_file_indirect_import_recs_req: PythonFileIndirectImportRecommendationsRequest,
) -> PythonFileImportRecommendations:
    py_package_helper = py_file_indirect_import_recs_req.py_package_helper
    get_commands: List[Get] = []
    for py_import in py_file_indirect_import_recs_req.py_file_info.imports:
        if py_import.modules_str not in py_package_helper.py_file_info_by_module:
            continue
        for name in py_import.names:
            get_commands.append(
                Get(
                    PythonFileIsNameDefinedResponse,
                    PythonFileIsNameDefinedRequest(
                        py_file_info=py_package_helper.py_file_info_by_module[py_import.modules_str],
                        source_import=py_import,
                        name=name,
                    ),
                )
            )
    defined_names_results: Tuple[PythonFileIsNameDefinedResponse] = await MultiGet(get_commands)

    indirect_imported_names: List[PythonFileIsNameDefinedResponse] = [
        res for res in defined_names_results if res.is_defined is False
    ]

    import_recs: List[PythonImportRecommendation] = []
    for indirect_imported_name in indirect_imported_names:
        res: PythonPackageImportsForNameResponse = await Get(
            PythonPackageImportsForNameResponse,
            PythonPackageImportsForNameRequest(
                py_package_helper=py_package_helper,
                name=indirect_imported_name.name,
            ),
        )
        if res.py_imports:
            import_recs.append(
                PythonImportRecommendation(
                    source_import=indirect_imported_name.source_import,
                    recommendations=res.py_imports
                )
            )
    return PythonFileImportRecommendations(
        py_file_info=py_file_indirect_import_recs_req.py_file_info,
        import_recommendations=tuple(import_recs),
    )


@rule("Gets Python file defined names from an import.")
async def is_named_defined_in_python_file(
    py_file_is_named_defined_req: PythonFileIsNameDefinedRequest,
) -> PythonFileIsNameDefinedResponse:
    return PythonFileIsNameDefinedResponse(
        py_file_info=py_file_is_named_defined_req.py_file_info,
        source_import=py_file_is_named_defined_req.source_import,
        name=py_file_is_named_defined_req.name,
        is_defined=py_file_is_named_defined_req.py_file_info.has_name(py_file_is_named_defined_req.name),
    )


@rule("Get import recommendations for name")
async def get_name_import_recommendations(
    py_package_imports_for_name_req: PythonPackageImportsForNameRequest,
) -> PythonPackageImportsForNameResponse:
    py_package_helper = py_package_imports_for_name_req.py_package_helper
    # Check STD Lib
    if python_utils.is_module_package(import_name=py_package_imports_for_name_req.name):
        return PythonPackageImportsForNameResponse(
            name=py_package_imports_for_name_req.name,
            py_imports=(PythonImport(modules=(), level=0, names=(py_package_imports_for_name_req.name,), aliases=()),),
        )

    # Check First party lib
    py_imports: List[PythonImport] = []
    for module_str, py_file_info in py_package_helper.py_file_info_by_module.items():
        if py_file_info.has_name(py_package_imports_for_name_req.name):
            py_imports.append(
                PythonImport(
                    modules=tuple(module_str.split(".")),
                    level=0,
                    names=(py_package_imports_for_name_req.name,),
                    aliases=(),
                ),
            ),
    if py_imports:
        return PythonPackageImportsForNameResponse(
            name=py_package_imports_for_name_req.name, py_imports=tuple(py_imports)
        )

    # Check Third party import
    for module_str, py_file_info in py_package_imports_for_name_req.py_package_helper.py_file_info_by_module.items():
        for py_import in py_file_info.imports:
            if (
                py_import.modules_str
                in py_package_imports_for_name_req.py_package_helper.py_file_info_by_import_module_str
            ):
                continue
            if py_package_imports_for_name_req.name in py_import.names:
                py_imports.append(
                    PythonImport(
                        modules=py_import.modules,
                        level=py_import.level,
                        names=(py_package_imports_for_name_req.name,),
                        aliases=(),
                    )
                )
    return PythonPackageImportsForNameResponse(name=py_package_imports_for_name_req.name, py_imports=tuple(py_imports))


def rules() -> Iterable[Rule]:
    return collect_rules()
