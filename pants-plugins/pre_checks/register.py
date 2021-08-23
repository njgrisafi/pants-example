from typing import Iterable

from pants.engine.rules import Rule

from . import pre_checks
from . import rules as pre_check_rules
from . import skip_field


def rules() -> Iterable[Rule]:
    return [
        *pre_checks.rules(),
        *pre_check_rules.rules(),
        *skip_field.rules(),
    ]
