import os
from typing import Iterable

from pants.engine.console import Console
from pants.engine.fs import DigestContents, PathGlobs, Workspace, Digest, CreateDigest
from pants.engine.goal import Goal, GoalSubsystem, LineOriented
from pants.engine.internals.build_files import BuildFileOptions
from pants.engine.internals.selectors import Get, MultiGet
from pants.engine.rules import Rule, collect_rules, goal_rule
from pants.engine.target import Targets
from pants.util.frozendict import FrozenDict

from .rules import BuildFileUpdateRequest, BuildFileUpdateResult


class CustomTailorSubsystem(LineOriented, GoalSubsystem):
    name = "custom-tailor"
    help = "Customizes BUILD file options to your liking."

    @classmethod
    def register_options(cls, register) -> None:
        super().register_options(register)
        register(
            "--target-types",
            type=list,
            metavar="[+-]type1,type2,...",
            default=["python_source"],
            help="Run on these target types, only `python_tests` and `python_sources` values are accepted.",
        )
        register(
            "--build-defaults",
            type=dict,
            help="Default settings for BUILD files under a given directory",
        )
        register(
            "--ignored-files",
            type=list,
            member_type=str,
            help="Optional mappings of files to ignore source targets. For example: ['app/api.py']",
        )

    @property
    def target_types(self) -> list[str]:
        return self.options.target_types

    @property
    def build_defaults(self) -> dict[str, dict[str, tuple[str, ...]]]:
        return self.options.build_defaults

    @property
    def ignored_files(self) -> list[str]:
        return self.options.ignored_files


class CustomTailor(Goal):
    subsystem_cls = CustomTailorSubsystem


@goal_rule
async def custom_tailor(
    console: Console,
    custom_tailor_subsystem: CustomTailorSubsystem,
    build_file_options: BuildFileOptions,
    targets: Targets,
    workspace: Workspace,
) -> CustomTailor:
    globs: list[str] = []
    for key in custom_tailor_subsystem.build_defaults:
        globs.extend(
            [*(os.path.join(key, "**", p) for p in build_file_options.patterns)]
        )
    all_build_files = await Get(
        DigestContents,
        PathGlobs(globs=globs),
    )
    build_files_to_update: dict[str, list[BuildFileUpdateRequest]] = {}
    for key in custom_tailor_subsystem.build_defaults:
        for build_file_content in all_build_files:
            if key not in build_file_content.path:
                continue
            if key not in build_files_to_update:
                build_files_to_update[key] = [
                    BuildFileUpdateRequest(
                        path=build_file_content.path,
                        lines=tuple(
                            build_file_content.content.decode("utf-8").splitlines()
                        ),
                        defaults=FrozenDict(custom_tailor_subsystem.build_defaults[key]),
                    )
                ]
                continue
            build_files_to_update[key].append(
                BuildFileUpdateRequest(
                    path=build_file_content.path,
                    lines=tuple(
                        build_file_content.content.decode("utf-8").splitlines()
                    ),
                    defaults=FrozenDict(custom_tailor_subsystem.build_defaults[key]),
                )
            )
    get_reqs: list[Get] = []
    for build_files in build_files_to_update.values():
        get_reqs.extend(
            [
                Get(BuildFileUpdateResult, BuildFileUpdateRequest, build_file)
                for build_file in build_files
            ]
        )

    res: tuple[BuildFileUpdateResult, ...] = await MultiGet(get_reqs)
    for r in res:
        digest = await Get(Digest, CreateDigest([r.file_content]))
        workspace.write_digest(
            digest=digest
        )
    return CustomTailor(exit_code=0)


def rules() -> Iterable[Rule]:
    return collect_rules()
