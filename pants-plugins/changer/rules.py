from pants.vcs.git import MaybeGitWorktree, GitWorktreeRequest, GitWorktree
from pants.engine.rules import rule, collect_rules, Get, MultiGet
from dataclasses import dataclass, field
from pants.util.strutil import softwrap
from pants.engine.engine_aware import EngineAwareReturnType

class GitTreeNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class GitInfoRequest:
    from_ref: str = "origin/master"


@dataclass(frozen=True)
class GitFileInfoReq:
    address: str

@dataclass(frozen=True)
class GitFileInfo:
    address: str
    is_new_file: bool
    modified_lines: tuple[str, ...] = field(default_factory=tuple)
    new_code: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class GitInfo:
    file_info: tuple[GitFileInfo, ...]


@rule
async def get_git_info(req: GitInfoRequest) -> GitInfo:
    maybe_git_worktree = await Get(MaybeGitWorktree, GitWorktreeRequest())
    git_worktree = maybe_git_worktree.git_worktree
    if git_worktree is None:
        raise GitTreeNotFoundError(
            "You are not running in a git worktree. Please ensure you are running this goal from a git project directory."
        )
    changed_files = git_worktree.changed_files()
    res: tuple[GitFileInfo, ...] = await MultiGet([Get(GitFileInfo, GitFileInfoReq(address=fp)) for fp in changed_files])
    return GitInfo(file_info=res)

@rule
async def get_git_file_info(req: GitFileInfoReq) -> GitFileInfo:
    maybe_git_worktree = await Get(MaybeGitWorktree, GitWorktreeRequest())
    git_worktree = maybe_git_worktree.git_worktree
    if git_worktree is None:
        raise GitTreeNotFoundError(
            "You are not running in a git worktree. Please ensure you are running this goal from a git project directory."
        )
    diff_info = git_worktree._git_binary._invoke_unsandboxed(
        git_worktree._create_git_cmdline(["diff", "origin/main", req.address])
    )
    diff_lines = diff_info.split("\n")
    diff_lines.pop(0)
    if "new file" in diff_lines[0]:
        return GitFileInfo(address=req.address, is_new_file=True)
    new_code = []
    modified_lines = []
    for line in diff_lines:
        if line.count("@@") == 2:
            removed_line = line.split()[1].split("-")[1].split(",")[0]
            added_line = line.split()[2].split("+")[1].split(",")[0]
            if added_line:
                modified_lines.append(added_line)
                modified_lines.append(str(int(added_line) + 1))
                modified_lines.append(str(int(added_line) + 2))
            if removed_line:
                modified_lines.append(removed_line)
                modified_lines.append(str(int(removed_line) + 1))
                modified_lines.append(str(int(removed_line) + 2))
        elif line.startswith("+") and line.count("+") == 1:
            new_code.append(line[1:].strip())

    return GitFileInfo(address=req.address, modified_lines=modified_lines, new_code=new_code, is_new_file=False)


def rules():
    return collect_rules()
