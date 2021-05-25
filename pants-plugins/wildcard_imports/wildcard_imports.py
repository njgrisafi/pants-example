from pants.engine.goal import Goal, GoalSubsystem, LineOriented
from pants.engine.rules import collect_rules, goal_rule
from pants.engine.console import Console
from pants.engine.target import Sources, Targets
from pants.engine.rules import Get
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest

from pants.engine.fs import Digest, DigestContents, FileContent

import re


from pants.backend.python.target_types import (
    PythonSources,
)


class WildcardImportsSubsystem(LineOriented, GoalSubsystem):
    name = "wildcard-imports"
    help = "Parses targets digest for wildcard imports"


class WildcardImports(Goal):
    subsystem_cls = WildcardImportsSubsystem


def has_wildcard_import(file_content: FileContent) -> bool:
    import_backslash = re.compile(rb"from[ ]+(\S+)[ ]+import[ ]+[*][ ]*")
    res = import_backslash.search(file_content.content)
    return res is not None


@goal_rule
async def wildcard_imports(
    console: Console, wildcard_imports_subsystem: WildcardImportsSubsystem, targets: Targets
) -> WildcardImports:
    # Get sources and contents
    sources = await Get(
        SourceFiles,
        SourceFilesRequest(
            [tgt.get(Sources) for tgt in targets], for_sources_types=(PythonSources,), enable_codegen=False
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
