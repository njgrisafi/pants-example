import re
from typing import Callable, List

from pants.backend.python.target_types import PythonLibrary, PythonSources, PythonTests
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.console import Console
from pants.engine.fs import Digest, DigestContents, FileContent
from pants.engine.goal import Goal, GoalSubsystem, LineOriented
from pants.engine.rules import Get, collect_rules, goal_rule
from pants.engine.target import RegisteredTargetTypes, Sources, Target, Targets, UnrecognizedTargetTypeException
from pants.util.filtering import and_filters, create_filters

from .import_fixer import ImportFixerHandler


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

    @property
    def target_types(self) -> List[str]:
        return self.options.target_types

    @property
    def include_top_level_package(self) -> bool:
        return self.options.include_top_level_package


class WildcardImports(Goal):
    subsystem_cls = WildcardImportsSubsystem


def has_wildcard_import(file_content: FileContent) -> bool:
    import_backslash = re.compile(rb"from[ ]+(\S+)[ ]+import[ ]+[*][ ]*")
    res = import_backslash.search(file_content.content)
    return res is not None


TargetFilter = Callable[[Target], bool]
allowed_target_types = RegisteredTargetTypes.create({tgt_type for tgt_type in [PythonLibrary, PythonTests]})


@goal_rule
async def wildcard_imports(
    console: Console, wildcard_imports_subsystem: WildcardImportsSubsystem, targets: Targets
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
    digest_contents = await Get(DigestContents, Digest, sources.snapshot.digest)

    # Parse contents for 'import *' patterns
    wildcard_import_sources = []
    for file_content in digest_contents:
        if has_wildcard_import(file_content):
            wildcard_import_sources.append(file_content.path)

    # No wild card imports!
    if len(wildcard_import_sources) == 0:
        return WildcardImports(exit_code=0)

    # Apply import fixes
    if wildcard_imports_subsystem.options.fix:
        # TODO: Maybe read 'package_root' from pants somehow?
        # Can also be configured from CLI args.
        import_fixer = ImportFixerHandler(
            package_root="app", include_top_level_package=wildcard_imports_subsystem.include_top_level_package
        )
        import_fixer.fix_targets(wildcard_import_sources)
        return WildcardImports(exit_code=0)

    # Output violating files and exit for failure
    with wildcard_imports_subsystem.line_oriented(console) as print_stdout:
        for source in wildcard_import_sources:
            print_stdout(source)
    return WildcardImports(exit_code=1)


def rules():
    return collect_rules()
