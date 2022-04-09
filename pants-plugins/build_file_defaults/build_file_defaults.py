from email.policy import default
import os
from tabnanny import check
from typing import Iterable

from pants.engine.console import Console
from pants.engine.fs import (CreateDigest, Digest, DigestContents, PathGlobs,
                             Workspace)
from pants.engine.goal import Goal, GoalSubsystem, LineOriented
from pants.engine.internals.build_files import BuildFileOptions
from pants.engine.internals.selectors import Get, MultiGet
from pants.engine.rules import Rule, collect_rules, goal_rule
from pants.engine.target import Targets
from pants.util.frozendict import FrozenDict

from .rules import BuildFileUpdateRequest, BuildFileUpdateResult


class BuildFileDefaultsSubsystem(LineOriented, GoalSubsystem):
    name = "build-file-defaults"
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
            "--check",
            type=bool,
            default=False,
            help="If provided, will not write changes and will only output the changes that would've been made.",
        )

    @property
    def target_types(self) -> list[str]:
        return self.options.target_types

    @property
    def build_defaults(self) -> dict[str, dict[str, tuple[str, ...]]]:
        return self.options.build_defaults

    @property
    def check(self) -> bool:
        return self.options.check


class BuildFileDefaults(Goal):
    subsystem_cls = BuildFileDefaultsSubsystem


@goal_rule
async def build_file_defaults(
    console: Console,
    build_file_defaults_subsystem: BuildFileDefaultsSubsystem,
    build_file_options: BuildFileOptions,
    targets: Targets,
    workspace: Workspace,
) -> BuildFileDefaults:
    globs: list[str] = []
    for key in build_file_defaults_subsystem.build_defaults:
        globs.extend(
            [*(os.path.join(key, "**", p) for p in build_file_options.patterns)]
        )
    all_build_files = await Get(
        DigestContents,
        PathGlobs(globs=globs),
    )
    build_files_to_update: dict[str, list[BuildFileUpdateRequest]] = {}
    for key in build_file_defaults_subsystem.build_defaults:
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
                        defaults=FrozenDict(
                            build_file_defaults_subsystem.build_defaults[key]
                        ),
                    )
                ]
                continue
            build_files_to_update[key].append(
                BuildFileUpdateRequest(
                    path=build_file_content.path,
                    lines=tuple(
                        build_file_content.content.decode("utf-8").splitlines()
                    ),
                    defaults=FrozenDict(build_file_defaults_subsystem.build_defaults[key]),
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
    changes_output = ""
    for r in res:
        if len(r.changes) == 0:
            continue
        changes_output += f"{r.file_content.path}:\n"
        for change in r.changes:
            changes_output += f"- {change}\n"
        if build_file_defaults_subsystem.check:
            continue
        digest = await Get(Digest, CreateDigest([r.file_content]))
        workspace.write_digest(digest=digest)
    if changes_output == "" or build_file_defaults_subsystem.check is False:
        return BuildFileDefaults(exit_code=0)
    with build_file_defaults_subsystem.line_oriented(console) as print_stdout:
        print_stdout(console.red("BUILD files need updates!"))
        print_stdout(changes_output)
        print_stdout(console.yellow("Run `./pants build-file-defaults` to autofix these issues."))
    return BuildFileDefaults(exit_code=1)


def rules() -> Iterable[Rule]:
    return collect_rules()
