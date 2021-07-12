from typing import Iterable

from import_fixer import (
    autoflake_rules,
    autoimport_rules,
    cross_imports_rules,
    import_fixer,
    indirect_imports_rules,
    isort_rules,
    wildcard_imports_rules,
    wildcard_imports_skip_field,
)
from pants.engine.rules import Rule


def rules() -> Iterable[Rule]:
    return [
        *import_fixer.rules(),
        *wildcard_imports_rules.rules(),
        *isort_rules.rules(),
        *autoflake_rules.rules(),
        *autoimport_rules.rules(),
        *wildcard_imports_skip_field.rules(),
        *cross_imports_rules.rules(),
        *indirect_imports_rules.rules(),
    ]
