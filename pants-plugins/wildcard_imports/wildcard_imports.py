from pants.engine.goal import Goal, GoalSubsystem, LineOriented
from pants.engine.rules import collect_rules, goal_rule
from pants.engine.console import Console
from pants.engine.target import Sources, Target, Targets
from pants.engine.rules import Get, rule
from pants.engine.target import HydratedSources, HydrateSourcesRequest
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.fs import SpecsSnapshot

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


# @goal_rule
# async def wildcard_imports(
#     console: Console, wildcard_imports_subsystem: WildcardImportsSubsystem, targets: Targets
# ) -> WildcardImports:
#     sources_call = []
#     with wildcard_imports_subsystem.line_oriented(console) as print_stdout:
#         for target in targets:
#             sources. await Get(
#                 HydratedSources,
#                 HydrateSourcesRequest(target.get(Sources), for_sources_types=(PythonSources,), enable_codegen=True),
#             )
#             # sources = Get(SourcesPaths, SourcesPathsRequest(target.get(Sources), for_sources_types=(PythonSources,)))
#             print_stdout(source_files)
#         sources = await Get(
#             SourceFiles,
#             SourceFilesRequest([targets]) 
#         )
#         print_stdout(sources)
#     return WildcardImports(exit_code=1)

@goal_rule
async def wildcard_imports(
    console: Console, wildcard_imports_subsystem: WildcardImportsSubsystem, specs_snapshot: SpecsSnapshot
) -> WildcardImports:
    with wildcard_imports_subsystem.line_oriented(console) as print_stdout:
        print_stdout(specs_snapshot.snapshot.digest)
        for f in specs_snapshot.snapshot.files:
            # sources = Get(SourcesPaths, SourcesPathsRequest(target.get(Sources), for_sources_types=(PythonSources,)))
            print_stdout(f)
    return WildcardImports(exit_code=1)


def rules():
    return collect_rules()
