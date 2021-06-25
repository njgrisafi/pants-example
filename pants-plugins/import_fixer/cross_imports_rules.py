from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

from import_fixer.cross_imports_rules_param_types import (
    PythonFileCrossImportStatsRequest,
    PythonFileCrossImportStatsResponse,
    PythonPackageCrossImportStatsRequest,
    PythonPackageCrossImportStatsResponse,
)
from pants.engine.rules import Get, MultiGet, Rule, collect_rules, rule
from pants.util.frozendict import FrozenDict


@rule(desc="Gets cross imports stats for a python package")
async def get_package_cross_import_stats(
    py_package_cross_import_req: PythonPackageCrossImportStatsRequest,
) -> PythonPackageCrossImportStatsResponse:

    get_cmds: List[Get] = []
    for py_file_info in py_package_cross_import_req.py_package_helper.py_file_info_by_module.values():
        get_cmds.append(
            Get(
                PythonFileCrossImportStatsResponse,
                PythonFileCrossImportStatsRequest(
                    py_file_info=py_file_info, py_package_helper=py_package_cross_import_req.py_package_helper
                ),
            )
        )
    cross_imports: Tuple[PythonFileCrossImportStatsResponse] = await MultiGet(get_cmds)
    filter_cross_imports = [cross_import for cross_import in cross_imports if bool(cross_import.cross_imports)]
    return PythonPackageCrossImportStatsResponse(
        cross_imports=filter_cross_imports,
    )


@rule(desc="Gets cross imports stats for a python file")
async def get_file_cross_import_stats(
    py_file_cross_import_req: PythonFileCrossImportStatsRequest,
) -> PythonFileCrossImportStatsResponse:
    cross_imports: Dict[str, int] = defaultdict(int)
    for py_import in py_file_cross_import_req.py_file_info.imports:
        if py_file_cross_import_req.py_package_helper.is_package_import(py_import=py_import):
            cross_imports[py_import.modules_str] += 1
    return PythonFileCrossImportStatsResponse(
        py_file_info=py_file_cross_import_req.py_file_info,
        cross_imports=FrozenDict(cross_imports),
    )


def rules() -> Iterable[Rule]:
    return collect_rules()
