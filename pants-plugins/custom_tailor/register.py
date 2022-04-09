from pants.engine.rules import Rule

from . import custom_tailor
from . import rules as custom_tailor_rules


def rules() -> list[Rule]:
    return [*custom_tailor.rules(), *custom_tailor_rules.rules()]
