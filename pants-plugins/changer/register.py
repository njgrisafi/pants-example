from typing import Iterable

from changer import rules as changer_rules
from changer import subsystem
from pants.engine.rules import Rule


def rules() -> Iterable[Rule]:
    return [*subsystem.rules(), *changer_rules.rules()]
