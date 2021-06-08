from pants.backend.python.target_types import PythonLibrary, PythonTests
from pants.engine.target import BoolField


class WildcardImportsField(BoolField):
    alias = "wildcard_imports"
    default = True
    help = "If true, will run wildcard-imports on targets."


def rules():
    return [
        PythonLibrary.register_plugin_field(WildcardImportsField),
        PythonTests.register_plugin_field(WildcardImportsField),
    ]
