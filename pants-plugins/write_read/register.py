from typing import Iterable

from pants.engine.rules import Rule

from .subsystem import rules as write_read_rules


def rules() -> Iterable[Rule]:
    return [*write_read_rules()]
