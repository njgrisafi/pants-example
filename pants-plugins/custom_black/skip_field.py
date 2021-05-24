from pants.backend.python.target_types import PythonLibrary, PythonTests
from pants.engine.target import BoolField


class SkipBlackField(BoolField):
    alias = "skip_black"
    default = True
    help = "If true, don't run Black on this target's code."


def rules():
    return [
        PythonLibrary.register_plugin_field(SkipBlackField),
        PythonTests.register_plugin_field(SkipBlackField),
    ]
