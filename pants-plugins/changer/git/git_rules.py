from changer.git.git_rules_params import (
    GitFileInfo,
    GitFileInfoReq,
    GitInfo,
    GitInfoRequest,
    GitTreeNotFoundError,
)
from changer.subsystem import ChangerSubsystem
from pants.engine.rules import Get, MultiGet, collect_rules, rule
from pants.vcs.git import GitWorktreeRequest, MaybeGitWorktree, GitBinaryException


@rule
async def get_git_info(
    _: GitInfoRequest, changer_subsystem: ChangerSubsystem
) -> GitInfo:
    maybe_git_worktree = await Get(MaybeGitWorktree, GitWorktreeRequest())
    git_worktree = maybe_git_worktree.git_worktree
    if git_worktree is None:
        raise GitTreeNotFoundError(
            "You are not running in a git worktree. Please ensure you are running this goal from a git project directory."
        )
    changed_files = git_worktree.changed_files(
        from_commit=changer_subsystem.from_commit
    )
    res: tuple[GitFileInfo, ...] = await MultiGet(
        [Get(GitFileInfo, GitFileInfoReq(address=fp)) for fp in changed_files]
    )
    return GitInfo(file_info=res)


@rule
async def get_git_file_info(
    req: GitFileInfoReq, changer_subsystem: ChangerSubsystem
) -> GitFileInfo:
    maybe_git_worktree = await Get(MaybeGitWorktree, GitWorktreeRequest())
    git_worktree = maybe_git_worktree.git_worktree
    if git_worktree is None:
        raise GitTreeNotFoundError(
            "You are not running in a git worktree. Please ensure you are running this goal from a git project directory."
        )
    try:
        diff_info = git_worktree._git_binary._invoke_unsandboxed(
            git_worktree._create_git_cmdline(
                ["diff", changer_subsystem.base_branch, req.address]
            )
        )
    except GitBinaryException as err:
        if "path not in the working tree" in str(err):
            return GitFileInfo(address=req.address, is_new_file=False, is_deleted=True)

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

    return GitFileInfo(
        address=req.address,
        modified_lines=modified_lines,
        new_code=new_code,
        is_new_file=False,
    )


def rules():
    return collect_rules()
