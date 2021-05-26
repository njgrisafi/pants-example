def generate_relative_module_key(app_python_file_path: str, include_top_level_package: bool) -> str:
    """
    Generates a relative module key that can be used with import statements.

    For example:
    ```
    generate_relative_module_key(
        app_python_file_path="app/module_2/a.py",
        include_top_level_package=True
    )
    ```
    Outputs: `app.module_2.a`

    Without top level package:
    ```
    generate_relative_module_key(
        app_python_file_path="app/module_2/a.py",
        include_top_level_package=False
    )
    ```
    Outputs: `module_2.a`

    Args:
        app_python_file_path (str): Relative path to python file.
        include_top_level_package (bool): True to include top level packages in module keys.

    Returns:
        str: Normalized module key that can be used for python import statements
    """
    relative_path = app_python_file_path
    if include_top_level_package is False:
        app_root = app_python_file_path.split("/")[0]
        relative_path = app_python_file_path.split(f"{app_root}/")[-1]
    return relative_path.split(".py")[0].replace("/", ".")
