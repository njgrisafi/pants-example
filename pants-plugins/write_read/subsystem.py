import random
from typing import Iterable

from pants.backend.python.target_types import PythonSources
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.console import Console
from pants.engine.fs import CreateDigest, Digest, DigestContents, FileContent, PathGlobs, Workspace
from pants.engine.goal import Goal, GoalSubsystem, LineOriented
from pants.engine.rules import Get, Rule, collect_rules, goal_rule
from pants.engine.target import Sources, Targets


class WriteReadSubsystem(LineOriented, GoalSubsystem):
    name = "write-read"
    help = "Writes something to targets."

    @classmethod
    def register_options(cls, register) -> None:
        super().register_options(register)
        register(
            "--text",
            type=str,
            default=None,
            help="Text to write to targets.",
        )

    @property
    def text(self) -> str:
        return self.options.text or "\n".join((['print("Updated")'] * random.randint(a=100000, b=200000)))


class WriteRead(Goal):
    subsystem_cls = WriteReadSubsystem


@goal_rule
async def write_read(
    console: Console, write_read_subsystem: WriteReadSubsystem, targets: Targets, workspace: Workspace
) -> WriteRead:

    # Get sources and contents
    sources = await Get(
        SourceFiles,
        SourceFilesRequest(
            [tgt.get(Sources) for tgt in targets], for_sources_types=(PythonSources,), enable_codegen=False
        ),
    )
    target_digest_contents: DigestContents = await Get(DigestContents, Digest, sources.snapshot.digest)
    original_digest_contents = await Get(DigestContents, PathGlobs(["app/**/*.py"]))

    # Perform fixes
    digest = await Get(
        Digest,
        CreateDigest(
            [
                FileContent(path=digest_content.path, content=write_read_subsystem.text.encode())
                for digest_content in target_digest_contents
            ]
        ),
    )
    workspace.write_digest(digest)

    # Reload package info
    updated_digest_contents = await Get(DigestContents, PathGlobs(["app/**/*.py"]))

    # THIS SHOULD NOT FAIL!
    assert original_digest_contents != updated_digest_contents, "This seems to be cached"
    return WriteRead(exit_code=0)


def rules() -> Iterable[Rule]:
    return collect_rules()
