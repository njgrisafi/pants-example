from pants.engine.goal import Goal, GoalSubsystem, LineOriented
from pants.engine.rules import collect_rules, goal_rule
from pants.engine.console import Console
from pants.engine.target import Sources, Targets
from pants.engine.rules import Get, rule
from pants.engine.target import HydratedSources, HydrateSourcesRequest

# from pants.engine.fs import CreateDigest, Digest, FileContent
# from pants.engine.target import SourcesPathsRequest, SourcesPaths


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
    with wildcard_imports_subsystem.line_oriented(console) as print_stdout:
        for target in targets:
            sources = await Get(
                HydratedSources,
                HydrateSourcesRequest(target.get(Sources), for_sources_types=(PythonSources,), enable_codegen=True),
            )
            # sources = Get(SourcesPaths, SourcesPathsRequest(target.get(Sources), for_sources_types=(PythonSources,)))
            source_files = sources.filespec["includes"]
            print_stdout(source_files)
    return WildcardImports(exit_code=1)


def rules():
    return collect_rules()
