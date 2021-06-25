import importlib
import re
from typing import Tuple

import autoflake
from pyflakes.messages import UndefinedExport, UndefinedName

match_import_star_re = re.compile(rb"from[ ]+(\S+)[ ]+import[ ]+[*][ ]*")
match_top_level_imports_re = re.compile(r"(^from[ ]+(\S+)[ ]+import[ ]+(.[(\n][^)]*[)]|.*)|^import.*)")


def generate_relative_module_key(py_file_path: str, include_top_level_package: bool) -> str:
    """
    Generates a relative module key that can be used with import statements.

    For example:
    ```
    generate_relative_module_key(
        py_file_path="app/module_2/a.py",
        include_top_level_package=True
    )
    ```
    Outputs: `app.module_2.a`

    Without top level package:
    ```
    generate_relative_module_key(
        py_file_path="app/module_2/a.py",
        include_top_level_package=False
    )
    ```
    Outputs: `module_2.a`

    Args:
        py_file_path (str): Relative path to python file from build root.
        include_top_level_package (bool): True to include top level packages in module keys.

    Returns:
        str: Normalized module key that can be used for python import statements
    """
    relative_path = py_file_path
    if include_top_level_package is False:
        app_root = py_file_path.split("/")[0]
        relative_path = py_file_path.split(f"{app_root}/")[-1]
    return relative_path.split(".py")[0].replace("/", ".").replace(".__init__", "")


def has_symbol_usage(symbol: str, file_content: str) -> bool:
    try:
        return bool(re.search(r"([^.\n\w]|^| |\n){}+([.|(|)||:|,])".format(symbol), file_content))
    except Exception:
        return False


def has_wildcard_import(file_content: bytes) -> bool:
    return bool(match_import_star_re.search(file_content))


def has_missing_import(file_content: bytes) -> bool:
    error_messages = autoflake.check(file_content)
    for message in error_messages:
        if isinstance(message, (UndefinedName, UndefinedExport)):
            return True


def get_missing_import_names(file_content: str) -> Tuple[str, ...]:
    error_messages = autoflake.check(file_content)
    missing_import_names = []
    for message in error_messages:
        if isinstance(message, (UndefinedName, UndefinedExport)):
            missing_import_names.extend(message.message_args)
    return tuple(set(missing_import_names))


def get_top_level_import_matches(file_context: bytes) -> Tuple[re.Match, ...]:
    return tuple(match_top_level_imports_re.finditer(file_context))


def is_module_package(import_name: str) -> bool:
    """
    Checks if import is a package existing in the current PYTHON_PATH.

    Args:
        name: package name

    Returns:
        True if import name exists in the current Python_PATH
        For example:
        ```python
            is_module_package(import_name="json")  # Outputs: True
            is_module_package(import_name="foobarfuzz")  # Outputs: False
        ```
    """
    package_specs = importlib.util.find_spec(import_name)
    try:
        importlib.util.module_from_spec(package_specs)
        return True
    except AttributeError:
        return False
