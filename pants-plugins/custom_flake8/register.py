from custom_flake8 import rule as custom_flake8_rules
from custom_flake8 import skip_field as custom_skip_field


def rules():
    return (*custom_flake8_rules.rules(), *custom_skip_field.rules())
