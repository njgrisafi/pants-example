from custom_black import rule as custom_black_rules
from custom_black import skip_field as custom_skip_field
from pants.backend.python.lint import python_fmt


def rules():
    return (*custom_black_rules.rules(), *python_fmt.rules(), *custom_skip_field.rules())
