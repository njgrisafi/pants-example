from pants.backend.python.target_types import PythonLibrary, PythonTests
from pants.engine.target import BoolField


class SkipPreChecksField(BoolField):
    alias = "skip_pre_checks"
    default = False
    help = "If true, don't run pre-checks on this target's code."


def rules():
    return [
        PythonLibrary.register_plugin_field(SkipPreChecksField),
        PythonTests.register_plugin_field(SkipPreChecksField),
    ]
