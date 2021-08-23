from textwrap import dedent

import pytest
from pants.backend.python.target_types import PythonLibrary
from pants.engine.fs import DigestContents, FileContent
from pants.testutil.rule_runner import QueryRule, RuleRunner

from .pre_checks import rules as subsystem_rules
from .rules import PreCheckFileRequest, PreCheckFileResult
from .rules import rules as pre_check_rules


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
    result = rule_runner.request(
        PreCheckFileResult,
        (
            PreCheckFileRequest(
                file_digest_contents=DigestContents(
                    (
                        FileContent(
                            path="f.py",
                            content=dedent(
                                """\
                            from unittest import TestCase


                            class TestCreation(TestCase):
                                def setUp(self, something):
                                    pass
                            """
                            ).encode(),
                        ),
                    )
                )
            ),
        ),
    )
    print(result)
