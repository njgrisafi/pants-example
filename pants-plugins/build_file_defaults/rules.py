import tokenize
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from pants.engine.fs import FileContent
from pants.engine.internals.parser import ParseError
from pants.engine.rules import collect_rules, rule
from pants.util.frozendict import FrozenDict
from pants.util.logging import LogLevel
from pants.util.memo import memoized


@dataclass(frozen=True)
class BuildFileUpdateRequest:
    path: str
    lines: tuple[str, ...]
    defaults: FrozenDict[str, tuple[str, ...]]
    target_types: tuple[str, ...] = ("python_sources",)

    @memoized
    def tokenize(self) -> list[tokenize.TokenInfo]:
        _bytes_stream = BytesIO("\n".join(self.lines).encode("utf-8"))
        try:
            return list(tokenize.tokenize(_bytes_stream.readline))
        except tokenize.TokenError as e:
            raise ParseError(f"Failed to parse {self.path}: {e}")

    def parse(self) -> list[dict[str, dict[str, Any]]]:
        tokens = iter(self.tokenize())

        def parse_body() -> list[dict[str, dict[str, Any]]]:
            current_name = None
            name_type = None
            build_file_contents: list[dict[str, dict[str, Any]]] = []
            curr_target = None
            pants_target = None
            for next_token in tokens:
                if (
                    next_token.type is tokenize.NL
                    or next_token.type is tokenize.NEWLINE
                    or next_token.type is tokenize.ENCODING
                    or next_token.type is tokenize.ENDMARKER
                ):
                    continue
                if next_token.type is tokenize.NAME and "python_" in next_token.string:
                    if pants_target is not None:
                        build_file_contents.append(curr_target)
                        name_type = None
                        current_name = None
                    pants_target = next_token.string
                    curr_target = {next_token.string: {}}
                    continue
                if next_token.type is tokenize.NAME and next_token.string not in [
                    "True",
                    "False",
                ]:
                    curr_target[pants_target][next_token.string] = None
                    current_name = next_token.string
                    continue
                if next_token.type is tokenize.OP and next_token.string in [
                    ",",
                    "(",
                    ")",
                ]:
                    continue
                if next_token.type is tokenize.OP and next_token.string == "=":
                    continue
                if next_token.type is tokenize.OP and next_token.string == "[":
                    name_type = "list"
                    continue
                if next_token.type is tokenize.OP and next_token.string == "]":
                    name_type = None
                    current_name = None
                    continue
                if name_type is None:
                    curr_target[pants_target][current_name] = next_token.string
                    current_name = None
                    continue
                if name_type == "list":
                    curr_target[pants_target][current_name] = (
                        curr_target[pants_target][current_name]
                        + [next_token.string.strip()]
                        if curr_target[pants_target][current_name] is not None
                        else [next_token.string]
                    )
            build_file_contents.append(curr_target)
            return build_file_contents

        return parse_body()

    def to_filecontent(
        self, build_file_body: list[dict[str, dict[str, Any]]]
    ) -> FileContent:
        lines = []
        for content in build_file_body:
            for key, value in content.items():
                if len(value) == 0:
                    lines.append(f"{key}()")
                    continue
                else:
                    lines.append(f"{key}(")
                for k, v in value.items():
                    if isinstance(v, str):
                        lines.append(f"    {k}={v},")
                        continue
                    lines.append(f"    {k}=[{', '.join(v)}],")
                lines.append(")\n")
        lines = "\n".join(lines)
        return FileContent(self.path, lines.encode("utf-8"))


@dataclass(frozen=True)
class BuildFileUpdateResult:
    file_content: FileContent
    changes: tuple[str, ...]

    def to_file_content(self) -> FileContent:
        lines = "\n".join(self.lines) + "\n"
        return FileContent(self.path, lines.encode("utf-8"))


@rule(desc="Update build file defaults", level=LogLevel.DEBUG)
async def update_build_file_defaults(
    build_file_req: BuildFileUpdateRequest,
) -> BuildFileUpdateResult:
    build_file_contents = build_file_req.parse()
    changes = []
    for content in build_file_contents:
        for target_type, options in build_file_req.defaults.items():
            if target_type not in content:
                continue
            for option in options:
                name, value = option.split("=")
                if name not in content[target_type]:
                    changes.append(f"Add {name}={value} in {target_type}")
                elif content[target_type][name] != value:
                    changes.append(f"Set {name}={value} in {target_type}")
                content[target_type][name] = value

    return BuildFileUpdateResult(
        file_content=build_file_req.to_filecontent(build_file_body=build_file_contents),
        changes=tuple(set(changes)),
    )


def rules():
    return [
        *collect_rules(),
    ]
