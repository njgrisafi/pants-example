from pants.backend.python.lint import python_fmt

from . import rules as autoflake_rules


def rules():
    return (*autoflake_rules.rules(), *python_fmt.rules())
