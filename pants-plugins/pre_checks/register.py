from typing import Iterable

from pants.engine.rules import Rule
from pre_checks import pre_checks
from pre_checks import rules as pre_check_rules
from pre_checks import skip_field


def rules() -> Iterable[Rule]:
    return [
        *pre_checks.rules(),
        *pre_check_rules.rules(),
        *skip_field.rules(),
    ]
