from pants.engine.rules import Rule

from . import custom_tailor


def rules() -> list[Rule]:
    return [*custom_tailor.rules()]
