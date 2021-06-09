from pants.backend.python.target_types import PythonLibrary, PythonTests
from pants.engine.target import BoolField


class WildcardImportsSkipField(BoolField):
    alias = "skip_wildcard_imports"
    default = True
    help = "If false, will run wildcard-imports on targets."


def rules():
    return [
        PythonLibrary.register_plugin_field(WildcardImportsSkipField),
        PythonTests.register_plugin_field(WildcardImportsSkipField),
    ]
