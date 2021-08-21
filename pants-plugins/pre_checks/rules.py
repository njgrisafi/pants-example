from dataclasses import dataclass

from pants.backend.python.lint.python_fmt import PythonFmtRequest
from pants.backend.python.target_types import InterpreterConstraintsField, PythonSources
from pants.core.goals.lint import LintRequest, LintResult, LintResults
from pants.core.util_rules.source_files import SourceFiles
from pants.engine.fs import Digest, DigestContents
from pants.engine.rules import collect_rules, rule
from pants.engine.target import FieldSet, Target
from pants.engine.unions import UnionRule
from pants.util.logging import LogLevel
from pre_checks.pre_checks import PreChecksSubsystem
from pre_checks.skip_field import SkipPreChecksField


@dataclass(frozen=True)
class PreCheckFilesRequest:
    source_files: SourceFiles


@rule(desc="Lint files for pre-checks", level=LogLevel.DEBUG)
async def pre_checks_files(field_sets: PreCheckRequest, pre_checks: PreChecksSubsystem) -> LintResults:
    

@rule(desc="Lint single file for pre-check", leve=LogLevel.DEBUG)
async def pre_check_file()



def rules():
    return [
        *collect_rules(),
    ]
