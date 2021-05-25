from pants.engine.goal import Goal, GoalSubsystem, LineOriented
from pants.engine.rules import collect_rules, goal_rule
from pants.engine.console import Console
from pants.engine.target import Sources, Targets, Target, UnrecognizedTargetTypeException
from pants.engine.rules import Get
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest

from pants.engine.fs import Digest, DigestContents, FileContent
from pants.util.filtering import and_filters, create_filters

import re
from typing import List, Callable


from pants.backend.python.target_types import (
    PythonLibrary,
    PythonSources,
    PythonTests,
)
from pants.engine.target import RegisteredTargetTypes


class WildcardImportsSubsystem(LineOriented, GoalSubsystem):
    name = "wildcard-imports"
    help = "Parses targets digest for wildcard imports"

    @classmethod
    def register_options(cls, register):
        super().register_options(register)
        register(
            "--target-types",
            type=list,
            metavar="[+-]type1,type2,...",
            help="Run on these target types, only `python_tests` and `python_library` values are accepted.",
        )

    @property
    def target_types(self) -> List[str]:
        print(self.options.target_types)
        return self.options.target_types


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
            *(create_filters(wildcard_imports_subsystem.options.target_types, filter_target_type)),
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

    # Return result
    if len(wildcard_import_sources) == 0:
        return WildcardImports(exit_code=0)
    with wildcard_imports_subsystem.line_oriented(console) as print_stdout:
        for source in wildcard_import_sources:
            print_stdout(source)
    return WildcardImports(exit_code=1)


def rules():
    return collect_rules()
