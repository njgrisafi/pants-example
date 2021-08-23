from textwrap import dedent

import pytest
from pants.core.target_types import PythonLibrary
from pants.engine.addresses import Address
from pants.testutil.rule_runner import QueryRule, RuleRunner
from pre_checks.pre_checks import rules as subsystem_rules
from pre_checks.rules import PreCheckFileRequest, PreCheckFileResult
from pre_checks.rules import rules as pre_check_rules


@pytest.fixture
def rule_runner() -> RuleRunner:
    return RuleRunner(
        rules=[
            *pre_check_rules(),
            *subsystem_rules(),
            QueryRule(PreCheckFileResult, [PreCheckFileRequest]),
        ],
        target_types=[PythonLibrary],
    )



def test_no_additional_args_failure() -> None:
    rule_runner = RuleRunner()
    rule_runner.write_files(
        {
            "project/BUILD": dedent(
                """\
             python_library(
                 name="my_tgt",
                 sources=["f.py"], 
             """
            ),
            "project/f.py": dedent(
                """\
                from unittest import TestCase


                class TestCreation(TestCase):
                    def setUp(self, something):
                        pass
                """
            ),
        },
    )
    tgt = rule_runner.get_target(Address("project", target_name="my_tgt"))
    #  Digest Contents?
    # pre_check_req = PreCheckFileRequest(file_digest_contents=)
