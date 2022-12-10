import json
from typing import Iterable

from pants.engine.console import Console
from pants.engine.goal import Goal, GoalSubsystem, LineOriented
from pants.engine.rules import Get, MultiGet, Rule, collect_rules, goal_rule
from pants.engine.target import Targets
from pants.option.option_types import BoolOption, DictOption

from changer.rules import GitInfoRequest, GitInfo


class ChangerSubsystem(LineOriented, GoalSubsystem):
    name = "changer"
    help = "Get git info from pants!"


class Changer(Goal):
    subsystem_cls = ChangerSubsystem


@goal_rule
async def import_blocker(
    changer_subsystem: ChangerSubsystem,
    console: Console,
) -> Changer:
    git_info = await Get(GitInfo, GitInfoRequest())
    if len(git_info.file_info) == 0:
        return Changer(exit_code=0)
    with changer_subsystem.line_oriented(console) as print_stdout:
        print_stdout("GIT INFO:")
        for file_info in git_info.file_info:
            if file_info.is_new_file:
                print_stdout(f"New File: {file_info.address}")
                continue
            print_stdout(f"Modified File: {file_info.address}")
            print_stdout("\n".join(file_info.new_code))
    return Changer(exit_code=0)


def rules() -> Iterable[Rule]:
    return collect_rules()
