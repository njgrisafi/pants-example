from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

from pants.core.goals.fmt import FmtResult
from pants.engine.fs import CreateDigest, Digest, DigestContents
from pants.engine.rules import Get, MultiGet, Rule, collect_rules, rule
from wildcard_imports.import_fixer import utils
from wildcard_imports.import_fixer.python_file_import_recs import (
    PythonFileImportRecommendations,
    PythonImportRecommendation,
)
from wildcard_imports.import_fixer.python_file_info import PythonImport, from_python_file_path
from wildcard_imports.isort_rules import IsortRequest
from wildcard_imports.rules_param_types import (
    DuplicateImportRecommendationsRequest,
    MissingImportRecommendationRequest,
    PythonFileDuplicateImportRecommendationsRequest,
    PythonFileImportDefinedNamesRequest,
    PythonFileImportDefinedNamesResponse,
    PythonFileMissingImportRecommendationsRequest,
    PythonFileSubmoduleImportRecommendationsRequest,
    PythonFileSubmoduleImportRecommendationsResponse,
    PythonFileTransitiveImportRecommendationsRequest,
    PythonFileTransitiveImportsRequest,
    PythonFileTransitiveImportsResponse,
    PythonFileTransitiveNamesRequest,
    PythonFileTransitiveNamesResponse,
    PythonFileWildcardImportRecommendationsRequest,
    SubmoduleTansitiveWildcardImportsRequest,
    SubmoduleTransitiveWildcardImportsResponse,
    TransitiveImportRecommendationsRequest,
    TransitiveImportRecommendationsResponse,
    WildcardImportRecommendationsRequest,
)


@rule(desc="Gets all wildcard import recommendations for a python file")
async def get_file_wildcard_import_recommendations(
    py_file_import_recommendations_req: PythonFileWildcardImportRecommendationsRequest,
) -> PythonFileImportRecommendations:
    get_commands: List[Get] = []
    for py_import in py_file_import_recommendations_req.py_file_info.imports:
        if py_import.is_wildcard_import:
            get_commands.append(
                Get(
                    PythonImportRecommendation,
                    WildcardImportRecommendationsRequest,
                    WildcardImportRecommendationsRequest(
                        source_py_file_info=py_file_import_recommendations_req.py_file_info,
                        wildcard_import=py_import,
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
    source_py_file_info = wildcard_import_rec_req.source_py_file_info
    py_wildcard_import = wildcard_import_rec_req.wildcard_import
    py_package_helper = wildcard_import_rec_req.py_package_helper
    visited = []
    import_recommendations: List[PythonImport] = []
    stack = [py_wildcard_import]
    print("=================================================")
    print(source_py_file_info)
    while stack:
        py_import = stack.pop()
        if py_import.modules_str in visited:
            continue
        visited.append(py_import.modules_str)
        try:
            transitive_py_file_info = py_package_helper.py_file_info_by_module[py_import.modules_str]
            print(transitive_py_file_info)
            res: TransitiveImportRecommendationsResponse = await Get(
                TransitiveImportRecommendationsResponse,
                TransitiveImportRecommendationsRequest(
                    py_file_info=source_py_file_info,
                    transitive_py_file_info=transitive_py_file_info,
                    py_package_helper=py_package_helper,
                ),
            )
            print(res.transitive_imports)
            import_recommendations.extend(res.transitive_imports)

            if transitive_py_file_info.is_module:
                raise KeyError("Trigger submodule check")
        except KeyError:
            # Check for submodule direct usages in source python file
            res: PythonFileSubmoduleImportRecommendationsResponse = await Get(
                PythonFileSubmoduleImportRecommendationsResponse,
                PythonFileSubmoduleImportRecommendationsRequest(
                    py_file_info=source_py_file_info, module_py_import=py_import, py_package_helper=py_package_helper
                ),
            )
            import_recommendations.extend(res.submodule_py_imports)

            # Queue all submodules for transitive checks
            res = await Get(
                SubmoduleTransitiveWildcardImportsResponse,
                SubmoduleTansitiveWildcardImportsRequest(
                    module_py_import=py_import, py_package_helper=py_package_helper
                ),
            )
            stack.extend(res.submodule_transitive_py_imports)
            continue

        # iterate on transitive 'import *' to find nested symbol usages
        for transitive_py_import in transitive_py_file_info.imports:
            if transitive_py_import.is_wildcard_import:
                stack.append(transitive_py_import)
    return PythonImportRecommendation(source_import=py_wildcard_import, recommendations=tuple(import_recommendations))


@rule(desc="Gets import recommendations for transitive file usages.")
async def get_transitive_file_import_recommendations(
    transitive_import_recs_request: TransitiveImportRecommendationsRequest,
) -> TransitiveImportRecommendationsResponse:
    import_recommendations = []
    # Check usage of direct transitive python file names
    res: PythonFileTransitiveNamesResponse = await Get(
        PythonFileTransitiveNamesResponse,
        PythonFileTransitiveNamesRequest(
            py_file_info=transitive_import_recs_request.py_file_info,
            transitive_py_file_info=transitive_import_recs_request.transitive_py_file_info,
            py_package_helper=transitive_import_recs_request.py_package_helper,
        ),
    )
    names = res.names
    if names:
        import_recommendations.append(
            PythonImport(
                modules=tuple(transitive_import_recs_request.transitive_py_file_info.module_key.split(".")),
                level=0,
                names=names,
                aliases=(),
            )
        )

    # Get usage of imports names from transitive python file
    res: PythonFileTransitiveImportsResponse = await Get(
        PythonFileTransitiveImportsResponse,
        PythonFileTransitiveImportsRequest(
            py_file_info=transitive_import_recs_request.py_file_info,
            transitive_py_file_info=transitive_import_recs_request.transitive_py_file_info,
            py_package_helper=transitive_import_recs_request.py_package_helper,
        ),
    )
    import_recommendations.extend(res.py_imports)
    return TransitiveImportRecommendationsResponse(transitive_imports=import_recommendations)


@rule("Gets a Python file submodule imports used.")
def get_submodule_import_recommendations_for_python_file(
    py_file_submodule_import_recs_req: PythonFileSubmoduleImportRecommendationsRequest,
) -> PythonFileSubmoduleImportRecommendationsResponse:
    module_directory_python_imports = []
    for (
        module_key,
        python_file_info,
    ) in py_file_submodule_import_recs_req.py_package_helper.py_file_info_by_module.items():
        symbol = python_file_info.module_key.split(".")[-1]
        if py_file_submodule_import_recs_req.module_py_import.modules_str in module_key and utils.has_symbol_usage(
            symbol=symbol, file_content=py_file_submodule_import_recs_req.py_file_info.file_content_str
        ):
            module_directory_python_imports.append(
                PythonImport(
                    modules=py_file_submodule_import_recs_req.module_py_import.modules,
                    level=0,
                    names=(symbol,),
                    aliases=(),
                )
            )
    return PythonFileSubmoduleImportRecommendationsResponse(submodule_py_imports=tuple(module_directory_python_imports))


@rule(desc="Gets a submodule transitive imports")
def get_submodule_transitive_wildcard_imports(
    submodule_transitive_import_req: SubmoduleTansitiveWildcardImportsRequest,
) -> SubmoduleTransitiveWildcardImportsResponse:
    submodule_python_imports = []
    for module_key in submodule_transitive_import_req.py_package_helper.py_file_info_by_module:
        if submodule_transitive_import_req.module_py_import.modules_str in module_key:
            submodule_python_imports.append(
                PythonImport(modules=tuple(module_key.split(".")), level=0, names=("*",), aliases=())
            )
    return SubmoduleTransitiveWildcardImportsResponse(submodule_transitive_py_imports=tuple(submodule_python_imports))


@rule(desc="Gets transitive wildcard import recommendations for a python import recommendation")
async def get_python_file_transitive_import_recommendations(
    py_transitive_file_import_rec_req: PythonFileTransitiveImportRecommendationsRequest,
) -> PythonFileImportRecommendations:
    # Update python files that import the current python file via a wildcard import
    wildcard_py_import = PythonImport(
        modules=tuple(py_transitive_file_import_rec_req.py_file_info.module_key.split(".")),
        level=0,
        names=("*",),
        aliases=(),
    )
    rec = PythonFileImportRecommendations(
        py_file_info=py_transitive_file_import_rec_req.transitive_py_file_info,
        import_recommendations=(PythonImportRecommendation(source_import=(), recommendations=(wildcard_py_import,)),),
    )
    digest = await Get(Digest, CreateDigest([rec.fixed_file_content]))
    res: FmtResult = await Get(
        FmtResult,
        IsortRequest,
        IsortRequest(argv=("--line-length=100000000", "--force-single-line-imports", "--combine-star"), digest=digest),
    )
    digest_contents: DigestContents = await Get(DigestContents, Digest, res.output)
    update_transitive_py_file_info = from_python_file_path(
        file_path=py_transitive_file_import_rec_req.transitive_py_file_info.path,
        file_content=digest_contents[0].content,
        module_key=py_transitive_file_import_rec_req.transitive_py_file_info.module_key
    )
    recs: PythonFileImportRecommendations = await Get(
        PythonFileImportRecommendations,
        PythonFileWildcardImportRecommendationsRequest(
            py_file_info=update_transitive_py_file_info,
            py_package_helper=py_transitive_file_import_rec_req.py_package_helper,
        ),
    )
    print(recs)
    return recs


@rule(desc="Gets duplicate import recommendations for a python file")
async def get_file_duplicate_import_recommendations(
    py_file_dup_import_rec_req: PythonFileDuplicateImportRecommendationsRequest,
) -> PythonFileImportRecommendations:
    imports_by_names: Dict[str, List[PythonImport]] = defaultdict(list)
    for py_import in py_file_dup_import_rec_req.py_file_info.imports:
        for name in py_import.names:
            imports_by_names[name].append(py_import)

    # Get all duplciate import names
    duplicate_import_by_names: Dict[str, List[PythonImport]] = defaultdict(list)
    for name, py_imports in imports_by_names.items():
        if len(py_imports) > 1:
            duplicate_import_by_names[name] = py_imports

    get_commands: List[Get] = []
    for name, py_imports in duplicate_import_by_names.items():
        get_commands.append(
            Get(
                PythonFileImportRecommendations,
                DuplicateImportRecommendationsRequest,
                DuplicateImportRecommendationsRequest(
                    py_file_info=py_file_dup_import_rec_req.py_file_info,
                    duplicate_imports=tuple(py_imports),
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
    duplicate_imports = dup_import_rec_req.duplicate_imports
    py_package_helper = dup_import_rec_req.py_package_helper
    duplicate_name = dup_import_rec_req.duplicate_name
    direct_name_definitions: List[PythonImport] = []
    for duplicate_import in duplicate_imports:
        if f"{duplicate_import.modules_str}.{duplicate_name}" in py_package_helper.py_file_info_by_module:
            direct_name_definitions.append(duplicate_import)
        elif duplicate_import.modules_str in py_package_helper.py_file_info_by_module:
            file_info = py_package_helper.py_file_info_by_module[duplicate_import.modules_str]
            if file_info.has_name(name=duplicate_name):
                direct_name_definitions.append(duplicate_import)
        else:
            direct_name_definitions.append(duplicate_import)
    non_direct_import_definitions = tuple(list(set(duplicate_imports) - set(direct_name_definitions)))
    import_recommendations = []
    for non_direct_import in non_direct_import_definitions:
        updated_names = tuple(set(non_direct_import.names) - {duplicate_name})
        import_recommendations.append(
            PythonImportRecommendation(
                source_import=non_direct_import,
                recommendations=(
                    PythonImport(
                        modules=non_direct_import.modules,
                        level=non_direct_import.level,
                        names=updated_names,
                        aliases=non_direct_import.aliases,
                    ),
                )
                if updated_names
                else (),
            )
        )
    return PythonFileImportRecommendations(
        py_file_info=dup_import_rec_req.py_file_info, import_recommendations=tuple(import_recommendations)
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
    missing_name = missing_import_rec_req.missing_name
    if utils.is_module_package(import_name=missing_name):
        return PythonImportRecommendation(
            source_import=None,
            recommendations=(PythonImport(modules=(), level=0, names=(missing_name,), aliases=()),),
        )

    for module_str, py_file_info in missing_import_rec_req.py_package_helper.py_file_info_by_module.items():
        if py_file_info.has_name(missing_name):
            return PythonImportRecommendation(
                source_import=None,
                recommendations=(
                    PythonImport(modules=tuple(module_str.split(".")), level=0, names=(missing_name,), aliases=()),
                ),
            )
    return PythonImportRecommendation(source_import=None, recommendations=())


@rule(desc="Get names used from transitive Python file")
async def get_names_used_from_transitive_python_file(
    py_file_transitive_names_req: PythonFileTransitiveNamesRequest,
) -> PythonFileTransitiveNamesResponse:
    names = []
    source_py_file = py_file_transitive_names_req.py_file_info
    transitive_py_file = py_file_transitive_names_req.transitive_py_file_info
    py_package_helper = py_file_transitive_names_req.py_package_helper
    file_content = source_py_file.file_content_str
    for py_class in transitive_py_file.classes:
        if utils.has_symbol_usage(symbol=py_class.name, file_content=file_content):
            names.append(py_class.name)
    for py_function in transitive_py_file.functions:
        if utils.has_symbol_usage(symbol=py_function.name, file_content=file_content):
            names.append(py_function.name)
    for py_constant in transitive_py_file.constants:
        for src_constant in source_py_file.constants:
            if py_constant.name == src_constant.name:
                break
        else:
            if utils.has_symbol_usage(symbol=py_constant.name, file_content=file_content):
                names.append(py_constant.name)

    if transitive_py_file.module_key in py_package_helper.ignored_import_names_by_module:
        names_to_skip = py_package_helper.ignored_import_names_by_module[transitive_py_file.module_key]
        names = set(names) - set(names_to_skip)
    return PythonFileTransitiveNamesResponse(names=tuple(names))


@rule("Gets imports used from transitive Python file")
async def get_imports_used_from_transitive_python_file(
    py_file_tansitive_imports_rec: PythonFileTransitiveImportsRequest,
) -> PythonFileTransitiveImportsResponse:
    py_imports_used = []
    transitive_py_file = py_file_tansitive_imports_rec.transitive_py_file_info
    source_py_file = py_file_tansitive_imports_rec.py_file_info
    py_package_helper = py_file_tansitive_imports_rec.py_package_helper
    for py_import in transitive_py_file.imports:
        defined_names = py_import.names
        if py_import.modules_str in py_package_helper.py_file_info_by_module:
            res: PythonFileImportDefinedNamesResponse = await Get(
                PythonFileImportDefinedNamesResponse,
                PythonFileImportDefinedNamesRequest(
                    py_file_info=py_package_helper.py_file_info_by_module[py_import.modules_str], py_import=py_import
                ),
            )
            defined_names = res.defined_names
        names_used = []
        for name in defined_names:
            if utils.has_symbol_usage(symbol=name, file_content=source_py_file.file_content_str):
                names_used.append(name)
        if py_import.modules_str in py_package_helper.ignored_import_names_by_module:
            names_to_skip = py_package_helper.ignored_import_names_by_module[py_import.modules_str]
            names_used = set(names_used) - set(names_to_skip)
        if names_used:
            py_imports_used.append(
                PythonImport(
                    modules=py_import.modules,
                    level=py_import.level,
                    names=tuple(names_used),
                    aliases=(),
                )
            )
    return PythonFileTransitiveImportsResponse(py_imports=tuple(py_imports_used))


@rule("Gets Python file defined names from an import.")
async def get_python_file_defined_names_from_import(
    py_file_import_defined_names_rec: PythonFileImportDefinedNamesRequest,
) -> PythonFileImportDefinedNamesResponse:
    defined_names = []
    for name in py_file_import_defined_names_rec.py_import.names:
        if py_file_import_defined_names_rec.py_file_info.has_name(name):
            defined_names.append(name)
    return PythonFileImportDefinedNamesResponse(defined_names=defined_names)


def rules() -> Iterable[Rule]:
    return collect_rules()
