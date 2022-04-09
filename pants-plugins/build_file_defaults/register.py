from pants.engine.rules import Rule

from . import build_file_defaults
from . import rules as custom_tailor_rules


def rules() -> list[Rule]:
    return [*build_file_defaults.rules(), *custom_tailor_rules.rules()]
