from pants.backend.python.lint import python_fmt
from custom_black import skip_field as custom_skip_field
from custom_black import rule as custom_black_rules


def rules():
    return (*custom_black_rules.rules(), *python_fmt.rules(), *custom_skip_field.rules())
