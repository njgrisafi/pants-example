from dataclasses import dataclass

@dataclass
class CheckCodeRulesRequest:
    address: str
    lines: tuple[str, ...]


@dataclass
class CodeRulesResponse:
    address: str
    rules: tuple[str, ...]
