from typing import Iterable

from pants.engine.rules import Rule
from custom_infer import rules as custom_infer_rules


def rules() -> Iterable[Rule]:
    return [
        *custom_infer_rules.rules(),
    ]