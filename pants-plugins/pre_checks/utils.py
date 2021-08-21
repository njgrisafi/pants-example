import re


def has_namespace_import_violation(namespace_name: str) -> bool:
    try:
        return bool(re.search(rf"(from {namespace_name}\.).*"))
    except Exception:
        return False
