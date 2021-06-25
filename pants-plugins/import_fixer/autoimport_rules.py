from dataclasses import dataclass

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
from pants.engine.target import FieldSet
from pants.util.logging import LogLevel
from pants.util.strutil import pluralize


@dataclass(frozen=True)
class AutoImportFieldSet(FieldSet):
    required_fields = (PythonSources,)

    sources: PythonSources


@dataclass(frozen=True)
class AutoImportRequest:
    digest: Digest


@dataclass(frozen=True)
class SetupRequest:
    request: AutoImportRequest


@dataclass(frozen=True)
class Setup:
    process: Process
    original_digest: Digest


@rule(level=LogLevel.DEBUG)
async def setup_autoimport(setup_request: SetupRequest) -> Setup:
    autoimport_req = setup_request.request
    autoimport_get = Get(
        VenvPex,
        PexRequest(
            output_filename="autoimport.pex",
            internal_only=True,
            requirements=PexRequirements(("autoimport>=0.7.0",)),
            interpreter_constraints=PexInterpreterConstraints(("CPython>=3.7",)),
            main=ConsoleScript("autoimport"),
        ),
    )
    snapshot_get = Get(Snapshot, Digest, autoimport_req.digest)
    snapshot, autoimport_pex = await MultiGet(snapshot_get, autoimport_get)
    process = await Get(
        Process,
        VenvPexProcess(
            autoimport_pex,
            argv=snapshot.files,
            input_digest=snapshot.digest,
            output_files=snapshot.files,
            description=f"Run autoimport on {pluralize(len(snapshot.files), 'file')}.",
            level=LogLevel.DEBUG,
        ),
    )
    return Setup(process, original_digest=snapshot.digest)


@rule(desc="Run autoimport", level=LogLevel.DEBUG)
async def autoimport_run(request: AutoImportRequest) -> FmtResult:
    setup = await Get(Setup, SetupRequest(request))
    result = await Get(ProcessResult, Process, setup.process)
    return FmtResult.from_process_result(
        result,
        original_digest=setup.original_digest,
        formatter_name="autoimport",
    )


def rules():
    return [
        *collect_rules(),
        *pex.rules(),
    ]
