import random
import time
from enum import Enum
from typing import Callable, Dict, Iterable, List, Tuple

from import_fixer.autoflake_rules import AutoflakeRequest
from import_fixer.autoimport_rules import AutoImportRequest
from import_fixer.cross_imports_rules_param_types import (
    PythonPackageCrossImportStatsRequest,
    PythonPackageCrossImportStatsResponse,
)
from import_fixer.isort_rules import IsortRequest
from import_fixer.python_connect import python_package_helper, python_utils
from import_fixer.python_connect.python_file_import_recs import PythonFileImportRecommendations
from import_fixer.python_connect.python_file_info import PythonFileInfo
from import_fixer.python_connect.python_package_helper import for_python_files
from import_fixer.wildcard_imports_rules_param_types import (
    PythonFileDuplicateImportRecommendationsRequest,
    PythonFileMissingImportRecommendationsRequest,
    PythonFileTransitiveImportRecommendationsRequest,
    PythonFileWildcardImportRecommendationsRequest,
)
from import_fixer.wildcard_imports_skip_field import WildcardImportsSkipField
from pants.backend.python.target_types import PythonLibrary, PythonSources, PythonTests
from pants.core.goals.fmt import FmtResult
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.console import Console
from pants.engine.fs import CreateDigest, Digest, DigestContents, FileContent, PathGlobs, Workspace
from pants.engine.goal import Goal, GoalSubsystem, LineOriented
from pants.engine.rules import Get, MultiGet, Rule, collect_rules, goal_rule
from pants.engine.target import RegisteredTargetTypes, Sources, Target, Targets, UnrecognizedTargetTypeException
from pants.util.filtering import and_filters, create_filters


class ImportFixerJobs(Enum):
    WILDCARD_IMPORTS = "wildcard_imports"
    CROSS_IMPORTS = "cross_imports"


class ImportFixerSubsystem(LineOriented, GoalSubsystem):
    name = "import-fixer"
    help = "Performs various import related jobs on targets digest and can perform autofixes."

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
            help="True to attempt autofix import issues.",
        )
        register(
            "--jobs",
            type=list,
            member_type=ImportFixerJobs,
            help="Jobs to run on targets.",
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
            "--ignored-names-by-module",
            type=dict,
            help=("Optional provided mapping of modules to names to ignore For example: {'common': ['freeze_time']}"),
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
    def jobs(self) -> List[ImportFixerJobs]:
        return self.options.jobs

    @property
    def ignored_names_by_module(self) -> Dict[str, Tuple[str, ...]]:
        return self.options.ignored_names_by_module


class ImportFixer(Goal):
    subsystem_cls = ImportFixerSubsystem


TargetFilter = Callable[[Target], bool]
allowed_target_types = RegisteredTargetTypes.create({tgt_type for tgt_type in [PythonLibrary, PythonTests]})


@goal_rule  # noqa: C901
async def import_fixer(
    console: Console, import_fixer_subsystem: ImportFixerSubsystem, targets: Targets, workspace: Workspace
) -> ImportFixer:
    # Filter targets to run on
    def filter_target_type(target_type: str) -> TargetFilter:
        if target_type not in allowed_target_types.aliases:
            raise UnrecognizedTargetTypeException(target_type, allowed_target_types)
        return lambda tgt: tgt.alias == target_type

    anded_filter: TargetFilter = and_filters(
        [
            *(create_filters(import_fixer_subsystem.target_types, filter_target_type)),
        ]
    )

    filtered_targets = [target for target in targets if anded_filter(target)]

    ##############################
    # Cross Imports
    ##############################
    if ImportFixerJobs.CROSS_IMPORTS in import_fixer_subsystem.jobs:
        all_py_files_digest_contents = await Get(DigestContents, PathGlobs(["app/**/*.py"]))
        py_package_helper = for_python_files(
            py_files_digest_contents=all_py_files_digest_contents,
            include_top_level_package=import_fixer_subsystem.include_top_level_package,
            ignored_import_names_by_module=import_fixer_subsystem.ignored_names_by_module,
        )
        cross_imports_res: PythonPackageCrossImportStatsResponse = await Get(
            PythonPackageCrossImportStatsResponse,
            PythonPackageCrossImportStatsRequest(py_package_helper=py_package_helper),
        )
        # Output violating files and exit for failure
        with import_fixer_subsystem.line_oriented(console) as print_stdout:
            print_stdout(cross_imports_res.to_json_str)
        return ImportFixer(exit_code=0)

    ##############################
    # Wildcard Imports
    ##############################
    wildcard_imports_targets = [
        target for target in filtered_targets if target.get(WildcardImportsSkipField).value is False
    ]

    # Get sources and contents
    sources: SourceFiles = await Get(
        SourceFiles,
        SourceFilesRequest(
            [tgt.get(Sources) for tgt in wildcard_imports_targets],
            for_sources_types=(PythonSources,),
            enable_codegen=False,
        ),
    )
    digest_contents: DigestContents = await Get(DigestContents, Digest, sources.snapshot.digest)

    # Parse contents for 'import *' patterns
    wildcard_import_sources = []
    for file_content in digest_contents:
        if python_utils.has_wildcard_import(file_content.content):
            wildcard_import_sources.append(file_content.path)

    # No wildcard imports!
    if len(wildcard_import_sources) == 0:
        return ImportFixer(exit_code=0)

    # Cheeck only, no fixes required
    if import_fixer_subsystem.fix is False:
        # Output violating files and exit for failure
        with import_fixer_subsystem.line_oriented(console) as print_stdout:
            print_stdout("Found 'import *' usage in the following files:")
            for source in wildcard_import_sources:
                print_stdout(source)
        return ImportFixer(exit_code=1)

    # Pre-Fix imports for with autoflake
    digest = await Get(Digest, PathGlobs(wildcard_import_sources))
    res: FmtResult = await Get(
        FmtResult,
        AutoflakeRequest,
        AutoflakeRequest(
            argv=("--in-place", "--remove-all-unused-imports"),
            digest=digest,
        ),
    )
    workspace.write_digest(res.output)

    # TODO: this is a hack because writting and reloading digest right away is not reliable.
    time.sleep(1)
    digest = await Get(Digest, PathGlobs(wildcard_import_sources))
    res: FmtResult = await Get(
        FmtResult,
        IsortRequest,
        IsortRequest(
            argv=("--force-single-line-imports", "--line-length=100000000", "--float-to-top"),
            digest=digest,
        ),
    )
    workspace.write_digest(res.output)

    # TODO: this is a hack because writting and reloading digest right away is not reliable.
    time.sleep(1)
    digest = await Get(Digest, PathGlobs(wildcard_import_sources))
    res: FmtResult = await Get(
        FmtResult,
        AutoImportRequest,
        AutoImportRequest(digest=digest),
    )
    workspace.write_digest(res.output)

    ##########################
    # Fix Wildcard Imports
    ##########################
    # Pre-Format imports for simpler runs
    # TODO: this is a hack because writting and reloading digest right away is not reliable.
    time.sleep(1)
    digest = await Get(Digest, PathGlobs(wildcard_import_sources))
    res: FmtResult = await Get(
        FmtResult,
        IsortRequest,
        IsortRequest(argv=("--line-length=100000000", "--combine-star", "--float-to-top"), digest=digest),
    )
    workspace.write_digest(res.output)

    # Load file content and get wildcard import reccommendations
    # TODO: this is a hack because writting and reloading digest right away is not reliable.
    time.sleep(1)
    all_py_files_digest_contents = await Get(DigestContents, PathGlobs(["app/**/*.py"]))
    py_package_helper = for_python_files(
        py_files_digest_contents=all_py_files_digest_contents,
        include_top_level_package=import_fixer_subsystem.include_top_level_package,
        ignored_import_names_by_module=import_fixer_subsystem.ignored_names_by_module,
    )
    wildcard_import_recs: Tuple[PythonFileImportRecommendations, ...] = await MultiGet(
        Get(
            PythonFileImportRecommendations,
            PythonFileWildcardImportRecommendationsRequest,
            PythonFileWildcardImportRecommendationsRequest(
                py_file_info=py_package_helper.get_python_file_info_from_file_path(fp),
                py_package_helper=py_package_helper,
            ),
        )
        for fp in wildcard_import_sources
    )

    # Get transitive file recommendations for changed files
    all_transitive_py_file_info: List[PythonFileInfo] = []
    get_commands: List[Get] = []
    for import_rec in wildcard_import_recs:
        transitive_files = [
            transitive_py_file_info
            for transitive_py_file_info in py_package_helper.get_transitive_python_files(
                source_py_file_info=import_rec.py_file_info
            )
            if transitive_py_file_info.path not in wildcard_import_sources
        ]
        get_commands.extend(
            list(
                Get(
                    PythonFileImportRecommendations,
                    PythonFileTransitiveImportRecommendationsRequest,
                    PythonFileTransitiveImportRecommendationsRequest(
                        py_file_info=import_rec.py_file_info,
                        transitive_py_file_info=transitive_py_file_info,
                        py_package_helper=py_package_helper,
                    ),
                )
                for transitive_py_file_info in transitive_files
                if transitive_py_file_info.path not in wildcard_import_sources
            )
        )
        all_transitive_py_file_info.extend(transitive_files)
    transitive_import_recs: Tuple[PythonFileImportRecommendations, ...] = ()
    if get_commands:
        transitive_import_recs = await MultiGet(get_commands)

    all_import_recs: List[PythonFileImportRecommendations] = list(
        set(list(wildcard_import_recs) + list(transitive_import_recs))
    )
    digest = await Get(Digest, CreateDigest([import_rec.fixed_file_content for import_rec in all_import_recs]))
    workspace.write_digest(digest)

    # Run autoflake and autoimport on changed files
    # TODO: this is a hack because writting and reloading digest right away is not reliable.
    time.sleep(1)
    digest = await Get(Digest, PathGlobs([import_rec.py_file_info.path for import_rec in wildcard_import_recs]))
    res: FmtResult = await Get(
        FmtResult,
        AutoflakeRequest,
        AutoflakeRequest(argv=("--in-place", "--remove-all-unused-imports"), digest=digest),
    )
    workspace.write_digest(res.output)

    ##########################
    # Fix Duplicate Imports
    ##########################
    # Pre-format imports with isort for simplier duplication fixes
    # TODO: this sleep is a hack because writting and reloading digest right away is not reliable.
    time.sleep(1)
    digest = await Get(Digest, PathGlobs([import_rec.py_file_info.path for import_rec in wildcard_import_recs]))
    res: FmtResult = await Get(
        FmtResult,
        IsortRequest,
        IsortRequest(argv=("--force-single-line-imports", "--line-length=100000000"), digest=digest),
    )
    workspace.write_digest(res.output)

    # TODO: This is a hack to force pants to not pull from cache.
    # There are occurrences on large files where it doesn't load latest content.
    # Until we figure that out the sleep and glob hack should remain
    time.sleep(1)
    previous_py_files_digest_contents = all_py_files_digest_contents
    all_py_files_digest_contents = await Get(
        DigestContents, PathGlobs(["app/**/*.py", f"{random.randint(a=0, b=10000)}"])
    )
    assert all_py_files_digest_contents != previous_py_files_digest_contents, "somethings really wrong"

    # Fix import duplicate imports
    py_package_helper = for_python_files(
        py_files_digest_contents=all_py_files_digest_contents,
        include_top_level_package=import_fixer_subsystem.include_top_level_package,
        ignored_import_names_by_module=import_fixer_subsystem.ignored_names_by_module,
    )
    dup_import_recs = await MultiGet(
        Get(
            PythonFileImportRecommendations,
            PythonFileDuplicateImportRecommendationsRequest,
            PythonFileDuplicateImportRecommendationsRequest(
                py_file_info=py_package_helper.get_python_file_info_from_file_path(import_rec.py_file_info.path),
                py_package_helper=py_package_helper,
            ),
        )
        for import_rec in wildcard_import_recs
    )
    digest = await Get(Digest, CreateDigest([import_rec.fixed_file_content for import_rec in dup_import_recs]))
    workspace.write_digest(digest)

    # TODO: this sleep is a hack because writting and reloading digest right away is not reliable.
    time.sleep(1)
    digest = await Get(Digest, PathGlobs([import_rec.py_file_info.path for import_rec in dup_import_recs]))
    res: FmtResult = await Get(
        FmtResult,
        IsortRequest,
        IsortRequest(argv=("--force-single-line-imports", "--line-length=100000000"), digest=digest),
    )
    workspace.write_digest(res.output)

    ##########################
    # Fix Missing Imports
    #########################
    # TODO: this sleep is a hack because writting and reloading digest right away is not reliable.
    time.sleep(1)
    previous_py_files_digest_contents = all_py_files_digest_contents
    all_py_files_digest_contents = await Get(
        DigestContents, PathGlobs(["app/**/*.py", f"{random.randint(a=0, b=1000)}"])
    )
    py_package_helper = for_python_files(
        py_files_digest_contents=all_py_files_digest_contents,
        include_top_level_package=import_fixer_subsystem.include_top_level_package,
        ignored_import_names_by_module=import_fixer_subsystem.ignored_names_by_module,
    )
    missing_import_files: List[FileContent] = []
    digest = await Get(Digest, PathGlobs([import_rec.py_file_info.path for import_rec in wildcard_import_recs]))
    digest_contents: DigestContents = await Get(DigestContents, Digest, digest)
    for file_content in digest_contents:
        if python_utils.has_missing_import(file_content=file_content.content):
            missing_import_files.append(file_content)
    missing_import_recs: Tuple[PythonFileImportRecommendations, ...] = await MultiGet(
        Get(
            PythonFileImportRecommendations,
            PythonFileMissingImportRecommendationsRequest,
            PythonFileMissingImportRecommendationsRequest(
                py_file_info=py_package_helper.get_python_file_info_from_file_path(fc.path),
                py_package_helper=py_package_helper,
            ),
        )
        for fc in missing_import_files
    )
    digest = await Get(Digest, CreateDigest([import_rec.fixed_file_content for import_rec in missing_import_recs]))
    workspace.write_digest(digest)

    # Final formatting
    # TODO: this is a hack because writting and reloading digest right away is not reliable.
    time.sleep(1)
    digest = await Get(Digest, PathGlobs([import_rec.py_file_info.path for import_rec in wildcard_import_recs]))
    res: FmtResult = await Get(
        FmtResult,
        IsortRequest,
        IsortRequest(
            argv=(
                "--line-length=120",
                "--use-parentheses",
                "--trailing-comma",
                "--multi-line=3",
                "--force-grid-wrap=0",
            ),
            digest=digest,
        ),
    )
    workspace.write_digest(res.output)
    return ImportFixer(exit_code=0)


def rules() -> Iterable[Rule]:
    return collect_rules()
