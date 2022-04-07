from typing import Callable, Iterable

from pants.backend.python.target_types import (PythonSourceTarget,
                                               PythonTestTarget)
from pants.engine.console import Console
from pants.engine.fs import Workspace
from pants.engine.goal import Goal, GoalSubsystem, LineOriented
from pants.engine.rules import Rule, collect_rules, goal_rule
from pants.engine.target import (RegisteredTargetTypes, Target, Targets,
                                 UnrecognizedTargetTypeException)
from pants.util.filtering import and_filters, create_filters


class CustomTailorSubsystem(LineOriented, GoalSubsystem):
    name = "custom-tailor"
    help = "Customizes BUILD file options to your liking."

    @classmethod
    def register_options(cls, register) -> None:
        super().register_options(register)
        register(
            "--target-types",
            type=list,
            metavar="[+-]type1,type2,...",
            help="Run on these target types, only `python_tests` and `python_sources` values are accepted.",
        )
        register(
            "--ignored-files",
            type=list,
            member_type=str,
            help="Optional mappings of files to ignore source targets. For example: ['app/api.py']",
        )

    @property
    def target_types(self) -> list[str]:
        return self.options.target_types

    @property
    def ignored_files(self) -> list[str]:
        return self.options.ignored_files


class CustomTailor(Goal):
    subsystem_cls = CustomTailorSubsystem


TargetFilter = Callable[[Target], bool]
allowed_target_types = RegisteredTargetTypes.create(
    {tgt_type for tgt_type in [PythonSourceTarget, PythonTestTarget]}
)


@goal_rule
async def custom_tailor(
    console: Console,
    custom_tailor_subsystem: CustomTailorSubsystem,
    targets: Targets,
    workspace: Workspace,
) -> CustomTailor:
    # Filter targets to run on
    def filter_target_type(target_type: str) -> TargetFilter:
        if target_type not in allowed_target_types.aliases:
            raise UnrecognizedTargetTypeException(target_type, allowed_target_types)
        return lambda tgt: tgt.alias == target_type

    anded_filter: TargetFilter = and_filters(
        [
            *(create_filters(custom_tailor_subsystem.target_types, filter_target_type)),
        ]
    )

    filtered_targets: list[Target] = [
        target for target in targets if anded_filter(target)
    ]

    if len(filtered_targets) == 0:
        return CustomTailor(exit_code=0)
    return CustomTailor(exit_code=0)


def rules() -> Iterable[Rule]:
    return collect_rules()
