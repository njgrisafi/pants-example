from custom_isort import rules as isort_rules
from custom_isort import skip_field
from pants.backend.python.lint import python_fmt


def rules():
    return (*isort_rules.rules(), *python_fmt.rules(), *skip_field.rules())
