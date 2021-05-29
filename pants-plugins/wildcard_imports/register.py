from typing import Iterable

from pants.engine.rules import Rule

from . import wildcard_import_rules, wildcard_imports


def rules() -> Iterable[Rule]:
    return [*wildcard_imports.rules(), *wildcard_import_rules.rules()]
