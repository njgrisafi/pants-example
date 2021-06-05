from typing import Callable, Dict, Iterable, List, Tuple

from pants.backend.python.target_types import PythonLibrary, PythonSources, PythonTests
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.console import Console
from pants.engine.fs import CreateDigest, Digest, DigestContents, PathGlobs, Workspace
from pants.engine.goal import Goal, GoalSubsystem, LineOriented
from pants.engine.rules import Get, MultiGet, Rule, collect_rules, goal_rule
from pants.engine.target import RegisteredTargetTypes, Sources, Target, Targets, UnrecognizedTargetTypeException
from pants.util.filtering import and_filters, create_filters

from . import utils
from .import_fixer import PythonFileImportRecommendations
from .python_package_helper import for_python_files
from .wildcard_import_rules import (
    PythonFileDuplicateImportRecommendationsRequest,
    PythonFileWildcardImportRecommendationsRequest,
    PythonTransitiveFileImportRecommendationsRequest,
)


class WildcardImportsSubsystem(LineOriented, GoalSubsystem):
    name = "wildcard-imports"
    help = "Parses targets digest for wildcard imports"

    @classmethod
    def register_options(cls, register) -> None:
        super().register_options(register)
        register(
            "--target-types",
            type=list,
            metavar="[+-]type1,type2,...",
            help="Run on these target types, only `python_tests` and `python_library` values are accepted.",
        )
        register(
            "--fix",
            type=bool,
            default=False,
            help="True to attempt autofix for widcard imports.",
        )
        register(
            "--include-top-level-package",
            type=bool,
            default=False,
            help=(
                "True to include top level package names in import statements. For example:\n"
                "True - results in 'from app.module_2.a import example_a'\n"
                "False - results in 'from module_2.a import example_a'"
            ),
        )
        register(
            "--ignore-duplicate-imports",
            type=bool,
            default=False,
            help="True to ignore duplicate import fixes in `--fix` result.",
        )
        register(
            "--ignored-names-by-module",
            type=dict,
            help=("Optional provided mapping of modules to names to ignore" "For example: {'common': ['freeze_time']}"),
        )

    @property
    def target_types(self) -> List[str]:
        return self.options.target_types

    @property
    def include_top_level_package(self) -> bool:
        return self.options.include_top_level_package

    @property
    def fix(self) -> bool:
        return self.options.fix

    @property
    def ignore_duplicate_imports(self) -> bool:
        return self.options.ignore_duplicate_imports

    @property
    def ignored_names_by_module(self) -> Dict[str, Tuple[str, ...]]:
        return self.options.ignored_names_by_module


class WildcardImports(Goal):
    subsystem_cls = WildcardImportsSubsystem


TargetFilter = Callable[[Target], bool]
allowed_target_types = RegisteredTargetTypes.create({tgt_type for tgt_type in [PythonLibrary, PythonTests]})


@goal_rule
async def wildcard_imports(
    console: Console, wildcard_imports_subsystem: WildcardImportsSubsystem, targets: Targets, workspace: Workspace
) -> WildcardImports:
    # Filter target types
    def filter_target_type(target_type: str) -> TargetFilter:
        if target_type not in allowed_target_types.aliases:
            raise UnrecognizedTargetTypeException(target_type, allowed_target_types)
        return lambda tgt: tgt.alias == target_type

    anded_filter: TargetFilter = and_filters(
        [
            *(create_filters(wildcard_imports_subsystem.target_types, filter_target_type)),
        ]
    )
    filtered_targets = [target for target in targets if anded_filter(target)]

    # Get sources and contents
    sources = await Get(
        SourceFiles,
        SourceFilesRequest(
            [tgt.get(Sources) for tgt in filtered_targets], for_sources_types=(PythonSources,), enable_codegen=False
        ),
    )
    digest_contents: DigestContents = await Get(DigestContents, Digest, sources.snapshot.digest)

    # Parse contents for 'import *' patterns
    wildcard_import_sources = []
    for file_content in digest_contents:
        if utils.has_wildcard_import(file_content.content):
            wildcard_import_sources.append(file_content.path)

    # No wildcard imports!
    if len(wildcard_import_sources) == 0:
        return WildcardImports(exit_code=0)

    # Perform fixes
    if wildcard_imports_subsystem.fix:
        all_py_files_digest_contents = await Get(DigestContents, PathGlobs(["app/**/*.py"]))
        py_package_helper = for_python_files(
            python_files_digest_contents=all_py_files_digest_contents,
            include_top_level_package=wildcard_imports_subsystem.include_top_level_package,
            ignored_import_names_by_module=wildcard_imports_subsystem.ignored_names_by_module,
        )
        wildcard_import_recs: Tuple[PythonFileImportRecommendations, ...] = await MultiGet(
            Get(
                PythonFileImportRecommendations,
                PythonFileWildcardImportRecommendationsRequest,
                PythonFileWildcardImportRecommendationsRequest(file_path=fp, python_package_helper=py_package_helper),
            )
            for fp in wildcard_import_sources
        )
        print(wildcard_import_recs)
        get_commands: List[Get] = []
        for import_rec in wildcard_import_recs:
            get_commands.extend(
                list(
                    Get(
                        PythonFileImportRecommendations,
                        PythonTransitiveFileImportRecommendationsRequest,
                        PythonTransitiveFileImportRecommendationsRequest(
                            transitive_python_file_info=transitive_python_file_info,
                            python_file_import_reccomendations=import_rec,
                            python_package_helper=py_package_helper,
                        ),
                    )
                    for transitive_python_file_info in py_package_helper.get_transtive_python_files_by_wildcard_import(
                        source_python_file_info=import_rec.python_file_info
                    )
                )
            )
        transitive_import_recs: Tuple[PythonFileImportRecommendations, ...] = await MultiGet(get_commands)
        all_import_recs: List[PythonFileImportRecommendations] = list(
            set(list(wildcard_import_recs) + list(transitive_import_recs))
        )
        digest = await Get(Digest, CreateDigest([import_rec.fixed_file_content for import_rec in all_import_recs]))
        workspace.write_digest(digest)
        if wildcard_imports_subsystem.ignore_duplicate_imports:
            return WildcardImports(exit_code=0)

        # Reload package info
        # all_py_files_digest_contents = await Get(DigestContents, PathGlobs(("app/**/*.py",)))
        new_py_files_digest_contents = await Get(DigestContents, PathGlobs(["app/**/*.py"]))

        # THIS SHOULD NOT FAIL!
        assert all_py_files_digest_contents != new_py_files_digest_contents, "This seems to be cached"
        # py_package_helper = for_python_files(
        #     python_files_digest_contents=all_py_files_digest_contents,
        #     include_top_level_package=wildcard_imports_subsystem.include_top_level_package,
        #     ignored_import_names_by_module=wildcard_imports_subsystem.ignored_names_by_module,
        # )
        # dup_import_recs = await MultiGet(
        #     Get(
        #         PythonFileImportRecommendations,
        #         PythonFileDuplicateImportRecommendationsRequest,
        #         PythonFileDuplicateImportRecommendationsRequest(
        #             file_path=import_rec.python_file_info.path,
        #             python_package_helper=py_package_helper
        #         )
        #     ) for import_rec in all_import_recs
        # )
        # digest = await Get(Digest, CreateDigest([import_rec.fixed_file_content for import_rec in dup_import_recs]))
        # workspace.write_digest(digest)
        # return WildcardImports(exit_code=0)

    # Output violating files and exit for failure
    with wildcard_imports_subsystem.line_oriented(console) as print_stdout:
        for source in wildcard_import_sources:
            print_stdout(source)
    return WildcardImports(exit_code=1)


def rules() -> Iterable[Rule]:
    return collect_rules()
