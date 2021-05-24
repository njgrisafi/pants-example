from pants.backend.python.target_types import PythonLibrary, PythonTests
from pants.engine.target import BoolField


class SkipFlake8Field(BoolField):
    alias = "skip_flake8"
    default = True
    help = "If true, don't run Flake8 on this target's code."


def rules():
    return [
        PythonLibrary.register_plugin_field(SkipFlake8Field),
        PythonTests.register_plugin_field(SkipFlake8Field),
    ]
