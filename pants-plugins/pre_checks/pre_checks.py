from typing import Iterable, List, Tuple

from pants.backend.python.target_types import PythonSources
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.console import Console
from pants.engine.fs import DigestContents, PathGlobs
from pants.engine.goal import Goal, GoalSubsystem, LineOriented
from pants.engine.internals.selectors import Get, MultiGet
from pants.engine.rules import Rule, collect_rules, goal_rule
from pants.engine.target import Sources, Targets

from .rules import PreCheckFileRequest, PreCheckFileResult
from .skip_field import SkipPreChecksField


class PreChecksSubsystem(LineOriented, GoalSubsystem):
    name = "pre-checks"
    help = "Analyzes code for require pre-checks."

    @classmethod
    def register_options(cls, register) -> None:
        super().register_options(register)
        register(
            "--skip",
            type=bool,
            default=False,
            help="Don't run pre-checks.",
        )


class PreChecks(Goal):
    subsystem_cls = PreChecksSubsystem


@goal_rule
async def pre_checks(console: Console, pre_check_subsystem: PreChecksSubsystem, targets: Targets) -> PreChecks:
    filter_targets = [tgt for tgt in targets if tgt.get(SkipPreChecksField).value is False]
    sources: SourceFiles = await Get(
        SourceFiles,
        SourceFilesRequest(
            [tgt.get(Sources) for tgt in filter_targets],
            for_sources_types=(PythonSources,),
            enable_codegen=False,
        ),
    )
    digest_contents: DigestContents = await Get(
        DigestContents, PathGlobs(sources.files)
    )
    get_cmds: List[Get] = []
    for file_content in digest_contents:
        get_cmds.append(
            Get(
                PreCheckFileResult,
                PreCheckFileRequest(
                    file_digest_contents=file_content
                )
            )
        )
    results: Tuple[PreCheckFileResult, ...] = await MultiGet(get_cmds)
    exit_code = 0
    with pre_check_subsystem.line_oriented(console=console) as print_stdout:
        for result in results:
            if result.status is False:
                print_stdout(
                    (
                        "============================\n"
                        f"Error found in {result.path} \n"
                        "---------------------------\n"
                        f"{result.message}"
                    )
                )
                exit_code = 1
    return PreChecks(exit_code=exit_code)


def rules() -> Iterable[Rule]:
    return collect_rules()
