from dataclasses import dataclass
from pathlib import PurePath
from typing import Iterable, List, Tuple

from pants.engine.collection import Collection
from pants.engine.rules import Get, MultiGet, Rule, collect_rules, rule
from pants.engine.target import HydratedSources, HydrateSourcesRequest, Sources, Target


@dataclass(frozen=True)
class FindNeedleRequest:
    """A request to find all targets with a `sources` file matching the `needle_filename`."""

    targets: Tuple[Target, ...]
    needle_filename: str


@dataclass(frozen=True)
class TargetsWithNeedle:
    targets: Tuple[Target, ...]


@rule
async def find_needle_in_haystack(find_needle: FindNeedleRequest) -> TargetsWithNeedle:
    all_hydrated_sources = await MultiGet(
        [Get(HydratedSources, HydrateSourcesRequest(tgt.get(Sources))) for tgt in find_needle.targets]
    )
    targets_with_needle: List[Target] = []
    for tgt, hydrated_sources in zip(find_needle.targets, all_hydrated_sources):
        for fp in hydrated_sources.snapshot.files:
            if PurePath(fp).name == find_needle.needle_filename:
                targets_with_needle.append(tgt)
                break
    return TargetsWithNeedle(targets=tuple(targets_with_needle))


def rules() -> Iterable[Rule]:
    return collect_rules()
