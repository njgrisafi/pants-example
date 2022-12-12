from changer import subsystem
from changer.git import git_rules
from pants.engine.rules import Rule


def rules() -> list[Rule]:
    return [*subsystem.rules(), *git_rules.rules()]
