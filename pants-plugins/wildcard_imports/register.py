from typing import Iterable

from pants.engine.rules import Rule

from . import autoflake_rules, autoimport_rules, isort_rules, wildcard_import_rules, wildcard_imports


def rules() -> Iterable[Rule]:
    return [
        *wildcard_imports.rules(),
        *wildcard_import_rules.rules(),
        *isort_rules.rules(),
        *autoflake_rules.rules(),
        *autoimport_rules.rules(),
    ]
