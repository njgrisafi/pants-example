from pants.backend.python.target_types import PythonLibrary, PythonSources, PythonTests
from pants.backend.python.util_rules import ancestor_files
from pants.engine.addresses import Address
from pants.engine.target import InferredDependencies
from pants.testutil.rule_runner import QueryRule, RuleRunner

from .rules import InferPythonCustomDependencies, import_rules


def test_infer_python_dependencies_tests_dependencies() -> None:
    rule_runner = RuleRunner(
        rules=[
            *import_rules(),
            *ancestor_files.rules(),
            QueryRule(InferredDependencies, (InferPythonCustomDependencies,)),
        ],
        target_types=[PythonLibrary, PythonTests],
    )
    rule_runner.set_options(
        [
            "--backend-packages=pants.backend.python",
            "--custom-infer-require-tests=api.py",
            "--source-root-patterns=app",
        ],
        env_inherit={"PATH", "PYENV_ROOT", "HOME"},
    )

    rule_runner.create_file("app/module_1/__init__.py")
    rule_runner.create_file("app/module_1/api.py")
    rule_runner.add_to_build_file("app/module_1", "python_library()")
    rule_runner.create_file("app/module_1/tests/__init__.py")
    rule_runner.create_file("app/module_1/tests/test_api.py")
    rule_runner.add_to_build_file("app/module_1/tests", "python_tests()")

    rule_runner.create_file("app/module_2/__init__.py")
    rule_runner.create_file("app/module_2/api.py")
    rule_runner.add_to_build_file("app/module_2", "python_library()")
    rule_runner.create_file("app/module_2/tests/__init__.py")
    rule_runner.create_file("app/module_2/tests/unit_tests/__init__.py")
    rule_runner.create_file("app/module_2/tests/unit_tests/test_api.py")
    rule_runner.add_to_build_file("app/module_2/tests/unit_tests", "python_tests()")

    rule_runner.create_file("app/module_3/a/b/__init__.py")
    rule_runner.create_file("app/module_3/a/b/api.py")
    rule_runner.add_to_build_file("app/module_3/a/b", "python_library()")
    rule_runner.create_file("app/module_3/tests/__init__.py")
    rule_runner.create_file("app/module_3/tests/unit_tests/__init__.py")
    rule_runner.create_file("app/module_3/tests/unit_tests/test_api.py")
    rule_runner.add_to_build_file("app/module_3/tests/unit_tests", "python_tests()")

    def run_dep_inference(address: Address) -> InferredDependencies:
        target = rule_runner.get_target(address)
        return rule_runner.request(
            InferredDependencies,
            [InferPythonCustomDependencies(target[PythonSources, PythonTests])],
        )

    assert run_dep_inference(Address("app/module_1/tests", relative_file_path="test_api.py")) == InferredDependencies(
        [
            Address("app/module_1", relative_file_path="api.py"),
        ],
        sibling_dependencies_inferrable=False,
    )


    assert run_dep_inference(Address("app/module_2/tests/unit_tests", relative_file_path="test_api.py")) == InferredDependencies(
        [
            Address("app/module_2", relative_file_path="api.py"),
        ],
        sibling_dependencies_inferrable=False,
    )

    assert run_dep_inference(Address("app/module_3/tests/unit_tests", relative_file_path="test_api.py")) == InferredDependencies(
        [
            Address("app/module_3/a/b", relative_file_path="api.py"),
        ],
        sibling_dependencies_inferrable=False,
    )
