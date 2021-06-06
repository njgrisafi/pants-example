from dataclasses import dataclass
from typing import Tuple

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
from pants.core.util_rules.source_files import SourceFiles
from pants.engine.fs import Digest, Snapshot
from pants.engine.internals.selectors import MultiGet
from pants.engine.process import Process, ProcessResult
from pants.engine.rules import Get, collect_rules, rule
from pants.engine.target import FieldSet
from pants.util.logging import LogLevel
from pants.util.strutil import pluralize


@dataclass(frozen=True)
class AutoflakeFieldSet(FieldSet):
    required_fields = (PythonSources,)

    sources: PythonSources


@dataclass(frozen=True)
class AutoflakeRequest:
    argv: Tuple[str, ...]
    digest: Digest


@dataclass(frozen=True)
class SetupRequest:
    request: AutoflakeRequest


@dataclass(frozen=True)
class Setup:
    process: Process
    original_digest: Digest


@rule(level=LogLevel.DEBUG)
async def setup_autoflake(setup_request: SetupRequest) -> Setup:
    autoflake_req = setup_request.request
    autoflake_get = Get(
        VenvPex,
        PexRequest(
            output_filename="autoflake.pex",
            internal_only=True,
            requirements=PexRequirements(("autoflake>=1.3,<=1.4",)),
            interpreter_constraints=PexInterpreterConstraints(("CPython>=3.7",)),
            main=ConsoleScript("autoflake"),
        ),
    )
    snapshot_get = Get(Snapshot, Digest, autoflake_req.digest)
    snapshot, autoflake_pex = await MultiGet(snapshot_get, autoflake_get)
    process = await Get(
        Process,
        VenvPexProcess(
            autoflake_pex,
            argv=(*autoflake_req.argv, *snapshot.files),
            input_digest=snapshot.digest,
            output_files=snapshot.files,
            description=f"Run autoflake on {pluralize(len(snapshot.files), 'file')}.",
            level=LogLevel.DEBUG,
        ),
    )
    return Setup(process, original_digest=snapshot.digest)


@rule(desc="Run autoflake with args", level=LogLevel.DEBUG)
async def autoflake_run(request: AutoflakeRequest) -> FmtResult:
    setup = await Get(Setup, SetupRequest(request))
    result = await Get(ProcessResult, Process, setup.process)
    return FmtResult.from_process_result(
        result,
        original_digest=setup.original_digest,
        formatter_name="autoflake",
    )


def rules():
    return [
        *collect_rules(),
        *pex.rules(),
    ]
