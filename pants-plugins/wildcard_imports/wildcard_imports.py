from pants.engine.goal import Goal, GoalSubsystem, LineOriented
from pants.engine.rules import collect_rules, goal_rule
from pants.engine.console import Console
from pants.engine.target import Sources, Targets
from pants.engine.rules import Get
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest

from pants.engine.fs import Digest, DigestContents


from pants.backend.python.target_types import (
    PythonSources,
)


class WildcardImportsSubsystem(LineOriented, GoalSubsystem):
    name = "wildcard-imports"
    help = "Parses targets digest for wildcard imports"


class WildcardImports(Goal):
    subsystem_cls = WildcardImportsSubsystem


@goal_rule
async def wildcard_imports(
    console: Console, wildcard_imports_subsystem: WildcardImportsSubsystem, targets: Targets
) -> WildcardImports:
    sources = await Get(
        SourceFiles,
        SourceFilesRequest(
            [tgt.get(Sources) for tgt in targets], for_sources_types=(PythonSources,), enable_codegen=False
        ),
    )
    digest_contents = await Get(DigestContents, Digest, sources.snapshot.digest)
    with wildcard_imports_subsystem.line_oriented(console) as print_stdout:
        print_stdout(digest_contents)
    return WildcardImports(exit_code=1)

def has_wildcard_import() -> bool:
    ...


def rules():
    return collect_rules()
