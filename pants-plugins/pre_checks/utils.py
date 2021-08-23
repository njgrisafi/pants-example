import re

namespace_import_re = re.compile(rb"(from app\.).*")
on_change_re = re.compile(rb"@on_change\(")
pytest_file_re = re.compile(r"/tests/+(.|)*test_[^\/].*(\S)*\.py")
additional_args_in_setup_teardown_re = re.compile(
    rb"(def setUp\(self,|def tearDown\(self|def setUpClass\(cls|def tearDownClass\(cls).*"
)


def has_namespace_import_violation(file_content: bytes) -> bool:
    return bool(namespace_import_re.search(file_content))


def has_on_change_handler_violation(file_path: str, file_content: bytes) -> bool:
    if bool(pytest_file_re.search(file_path)):
        return False
    if (
        bool(on_change_re.search(file_content)) is False
        and (file_path.endswith("models.py") or file_path.endswith("models.py")) is False
    ):
        return False

    for line in file_content.split(b"\n")[-3:]:
        if b"on_change_patch_module" in line:
            return False

    return True


def has_additional_args_in_setup_teardown(file_content: bytes) -> bool:
    return bool(additional_args_in_setup_teardown_re.search(file_content))
