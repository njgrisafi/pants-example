from dataclasses import dataclass
from typing import Tuple

from pants.backend.python.lint.isort.skip_field import SkipIsortField
from pants.backend.python.target_types import ConsoleScript, PythonSources
from pants.backend.python.util_rules import pex
from pants.backend.python.util_rules.pex import (
    PexInterpreterConstraints,
    PexRequest,
    PexRequirements,
    VenvPex,
    VenvPexProcess,
)
from pants.core.goals.fmt import FmtResult
from pants.engine.fs import Digest, Snapshot
from pants.engine.internals.selectors import MultiGet
from pants.engine.process import Process, ProcessResult
from pants.engine.rules import Get, collect_rules, rule
from pants.engine.target import FieldSet, Target
from pants.util.logging import LogLevel
from pants.util.strutil import pluralize


@dataclass(frozen=True)
class IsortFieldSet(FieldSet):
    required_fields = (PythonSources,)

    sources: PythonSources

    @classmethod
    def opt_out(cls, tgt: Target) -> bool:
        return tgt.get(SkipIsortField).value


@dataclass(frozen=True)
class IsortRequest:
    argv: Tuple[str, ...]
    digest: Digest


@dataclass(frozen=True)
class SetupRequest:
    request: IsortRequest


@dataclass(frozen=True)
class Setup:
    process: Process
    original_digest: Digest


@rule(level=LogLevel.DEBUG)
async def setup_isort(setup_request: SetupRequest) -> Setup:
    isort_req = setup_request.request
    isort_get = Get(
        VenvPex,
        PexRequest(
            output_filename="isort.pex",
            internal_only=True,
            requirements=PexRequirements(("isort[pyproject]>=5.5.1,<5.6", "setuptools")),
            interpreter_constraints=PexInterpreterConstraints(("CPython>=3.7",)),
            main=ConsoleScript("isort"),
        ),
    )
    snapshot_get = Get(Snapshot, Digest, isort_req.digest)
    snapshot, isort_pex = await MultiGet(snapshot_get, isort_get)
    process = await Get(
        Process,
        VenvPexProcess(
            isort_pex,
            argv=tuple(list(isort_req.argv) + list(snapshot.files)),
            input_digest=snapshot.digest,
            output_files=snapshot.files,
            description=f"Run isort on {pluralize(len(snapshot.files), 'file')}.",
            level=LogLevel.DEBUG,
        ),
    )
    return Setup(process, original_digest=snapshot.digest)


@rule(desc="Run isort with args", level=LogLevel.DEBUG)
async def isort_run(request: IsortRequest) -> FmtResult:
    setup = await Get(Setup, SetupRequest(request))
    result = await Get(ProcessResult, Process, setup.process)
    return FmtResult.from_process_result(
        result,
        original_digest=setup.original_digest,
        formatter_name="isort",
        strip_chroot_path=True,
    )


def rules():
    return [
        *collect_rules(),
        *pex.rules(),
    ]
