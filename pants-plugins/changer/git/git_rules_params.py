from dataclasses import dataclass, field


class GitTreeNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class GitInfoRequest:
    ...


@dataclass(frozen=True)
class GitFileInfoReq:
    address: str


@dataclass(frozen=True)
class GitFileInfo:
    address: str
    is_new_file: bool
    is_deleted: bool = field(default=False)
    modified_lines: tuple[str, ...] = field(default_factory=tuple)
    new_code: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class GitInfo:
    file_info: tuple[GitFileInfo, ...]
