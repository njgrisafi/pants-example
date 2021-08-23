from dataclasses import dataclass
from typing import List, Tuple

from pants.engine.fs import DigestContents
from pants.engine.rules import collect_rules, rule
from pants.util.logging import LogLevel

from .utils import (
    has_additional_args_in_setup_teardown,
    has_namespace_import_violation,
    has_on_change_handler_violation,
)


@dataclass(frozen=True)
class PreCheckFileRequest:
    file_digest_contents: DigestContents


@dataclass(frozen=True)
class PreCheckFileResult:
    path: str
    status: bool
    output: Tuple[str, ...]

    @property
    def message(self) -> str:
        return "\n".join(self.output)


@rule(desc="Lint file for pre-checks", level=LogLevel.DEBUG)
async def pre_check_file(pre_check_file_req: PreCheckFileRequest) -> PreCheckFileResult:
    status = True
    output: List[str] = []

    if has_namespace_import_violation(file_content=pre_check_file_req.file_digest_contents.content):
        status = False
        output.append("You should not import from app.*")
    if has_on_change_handler_violation(
        file_path=pre_check_file_req.file_digest_contents.path,
        file_content=pre_check_file_req.file_digest_contents.content,
    ):
        status = False
        output.append("No on_change_patch_module in last 3 lines of file")
    if has_additional_args_in_setup_teardown(file_content=pre_check_file_req.file_digest_contents.content):
        status = False
        output.append(
            (
                "In the test class, methods setUp/tearDown/setUpClass/tearDownClass "
                "should not have additional arguments after cls/self. "
                "If you need to patch, refer to example class BillingPlanTestE."
            )
        )
    return PreCheckFileResult(path=pre_check_file_req.file_digest_contents.path, status=status, output=tuple(output))


def rules():
    return [
        *collect_rules(),
    ]
