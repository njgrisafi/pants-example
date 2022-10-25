from typing import Iterable

from custom_infer import options
from pants.engine.rules import Rule


def rules() -> Iterable[Rule]:
    return [*options.rules()]
