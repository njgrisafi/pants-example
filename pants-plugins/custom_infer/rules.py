from typing import Iterable, cast

from pants.backend.python.target_types import PythonSources, PythonTestsSources
from pants.backend.python.util_rules import ancestor_files
from pants.backend.python.util_rules.ancestor_files import (
    AncestorFiles,
    AncestorFilesRequest,
)
from pants.engine.addresses import Address, AddressInput, UnparsedAddressInputs, Addresses
from pants.engine.fs import DigestContents, PathGlobs
from pants.engine.internals.graph import Owners, OwnersRequest
from pants.engine.rules import Get, MultiGet, Rule, SubsystemRule, rule
from pants.engine.target import (
    HydratedSources,
    HydrateSourcesRequest,
    InferDependenciesRequest,
    InferredDependencies,
)
from pants.base.specs import (
    AddressSpecs,
)
from pants.engine.unions import UnionRule
from pants.option.subsystem import Subsystem
from pants.python.python_setup import PythonSetup


class CustomInferSubsystem(Subsystem):
    options_scope = "custom-infer"
    help = "Options controlling which dependencies will be inferred for Python targets."

    @classmethod
    def register_options(cls, register) -> None:
        super().register_options(register)
        register(
            "--require-tests",
            default=[],
            type=list,
            help="Include parent modules when inferrering these targets.",
        )

    @property
    def require_tests(self) -> list[str]:
        return cast(list[str], self.options.require_tests)


class InferPythonCustomDependencies(InferDependenciesRequest):
    infer_from = PythonSources


@rule(desc="Inferring Python dependencies required for tests")
async def infer_python_dependencies_tests_dependencies(
    request: InferPythonCustomDependencies,
    custom_infer_subsystem: CustomInferSubsystem,
) -> InferredDependencies:
    if len(custom_infer_subsystem.require_tests) == 0 or isinstance(request.sources_field, PythonTestsSources) is False:
        return InferredDependencies(dependencies=[], sibling_dependencies_inferrable=False)

    hydrated_sources = await Get(HydratedSources, HydrateSourcesRequest(request.sources_field))
    extra_custom_files = await MultiGet(
        Get(
            AncestorFiles,
            AncestorFilesRequest(file_pattern, hydrated_sources.snapshot),
        )
        for file_pattern in custom_infer_subsystem.require_tests
    )

    files = list(hydrated_sources.snapshot.files)
    for ancestor_file in extra_custom_files:
        files.extend(ancestor_file.snapshot.files)

    owners = await MultiGet(Get(Owners, OwnersRequest((f,))) for f in set(files))
    addresses: list[Address] = []
    for owner in owners:
        address = owner[0]
        if address.filename.split("/")[-1] in custom_infer_subsystem.require_tests:
            addresses.append(address)
            continue
        relative_dir = "/".join(str(address.filename).split("/tests/")[:-1]) or "."
        path_globs = []
        for file_pattern in custom_infer_subsystem.require_tests:
            path_globs.extend(
                [
                    f"{relative_dir}/{file_pattern}",
                    f"{relative_dir}/**/**/{file_pattern}",
                ]
            )
        tests_digest = await Get(
            DigestContents,
            PathGlobs(path_globs),
        )
        if tests_digest.count == 0:
            continue
        res = await Get(Addresses, UnparsedAddressInputs(values=[x.path for x in tests_digest], owning_address=None))
        addresses.extend(res)
    return InferredDependencies(dependencies=addresses, sibling_dependencies_inferrable=False)


def import_rules() -> Iterable[Rule]:
    return [
        SubsystemRule(CustomInferSubsystem),
        SubsystemRule(PythonSetup),
        infer_python_dependencies_tests_dependencies,
    ]


def rules() -> Iterable[Rule]:
    return [
        *import_rules(),
        *ancestor_files.rules(),
        UnionRule(InferDependenciesRequest, InferPythonCustomDependencies),
    ]
