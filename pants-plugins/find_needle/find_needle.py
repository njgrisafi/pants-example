from typing import Iterable

from find_needle.rules import FindNeedleRequest, TargetsWithNeedle
from pants.engine.console import Console
from pants.engine.goal import Goal, GoalSubsystem, LineOriented
from pants.engine.internals.selectors import Get
from pants.engine.rules import Rule, collect_rules, goal_rule
from pants.engine.target import Targets


class FindNeedleSubsystem(LineOriented, GoalSubsystem):
    name = "find-needle"
    help = "Finds the needle (filename) in the hay stack."

    @classmethod
    def register_options(cls, register) -> None:
        super().register_options(register)
        register(
            "--needle-name",
            type=str,
            help="Needle name (fdilename) to search for.",
        )

    @property
    def needle_name(self) -> str:
        return self.options.needle_name


class FindNeedle(Goal):
    subsystem_cls = FindNeedleSubsystem


@goal_rule
async def find_needle(console: Console, find_needle_subsystem: FindNeedleSubsystem, targets: Targets) -> FindNeedle:

    target_with_needle: TargetsWithNeedle = await Get(
        TargetsWithNeedle, FindNeedleRequest(targets=targets, needle_filename=find_needle_subsystem.needle_name)
    )
    with find_needle_subsystem.line_oriented(console) as print_stdout:
        if len(target_with_needle.targets) == 0:
            print_stdout(f"{find_needle_subsystem.needle_name} not found :(")
            return FindNeedle(exit_code=1)
        print_stdout(f"{find_needle_subsystem.needle_name} found {len(target_with_needle.targets)} times!")
        return FindNeedle(exit_code=0)


def rules() -> Iterable[Rule]:
    return collect_rules()
