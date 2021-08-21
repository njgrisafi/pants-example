from typing import Iterable

from pants.backend.python.target_types import PythonSources
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.console import Console
from pants.engine.goal import Goal, GoalSubsystem, LineOriented
from pants.engine.internals.selectors import Get
from pants.engine.rules import Rule, collect_rules, goal_rule
from pants.engine.target import Sources, Targets


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
    sources: SourceFiles = await Get(
        SourceFiles,
        SourceFilesRequest(
            [tgt.get(Sources) for tgt in targets],
            for_sources_types=(PythonSources,),
            enable_codegen=False,
        ),
    )
    return PreChecks(exit_code=0)


def rules() -> Iterable[Rule]:
    return collect_rules()
