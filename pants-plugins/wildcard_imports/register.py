from typing import Iterable

from pants.engine.rules import Rule
from wildcard_imports import (
    autoflake_rules,
    autoimport_rules,
    isort_rules,
    wildcard_imports,
    wildcard_imports_rules,
    wildcard_imports_skip_field,
)


def rules() -> Iterable[Rule]:
    return [
        *wildcard_imports.rules(),
        *wildcard_imports_rules.rules(),
        *isort_rules.rules(),
        *autoflake_rules.rules(),
        *autoimport_rules.rules(),
        *wildcard_imports_skip_field.rules(),
    ]
