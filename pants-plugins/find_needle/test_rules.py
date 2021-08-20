from pants.engine.addresses import Address
from pants.engine.fs import EMPTY_DIGEST, Snapshot
from pants.engine.target import HydratedSources, HydrateSourcesRequest, Sources, Target
from pants.testutil.rule_runner import MockGet, run_rule_with_mocks

from .rules import FindNeedleRequest, TargetsWithNeedle, find_needle_in_haystack


class MockTarget(Target):
    alias = "mock_target"
    core_fields = (Sources,)


def test_find_needle_in_haystack() -> None:
    tgt1 = MockTarget({}, Address("", target_name="t1"))
    tgt2 = MockTarget({}, Address("", target_name="t2"))
    tgt3 = MockTarget({}, Address("", target_name="t3"))
    find_needles_request = FindNeedleRequest(targets=(tgt1, tgt2, tgt3), needle_filename="needle.txt")

    def mock_hydrate_sources(request: HydrateSourcesRequest) -> HydratedSources:
        # Our rule only looks at `HydratedSources.snapshot.files`, so we mock all other fields. We
        # include the file `needle.txt` for the target `:t2`, but no other targets.
        files = (
            ("needle.txt", "foo.txt")
            if request.field.address.target_name == "t2"
            else ("foo.txt", "bar.txt")
        )
        mock_snapshot = Snapshot(EMPTY_DIGEST, files=files, dirs=())
        return HydratedSources(mock_snapshot, filespec={}, sources_type=None)

    result: TargetsWithNeedle = run_rule_with_mocks(
        find_needle_in_haystack,
        rule_args=[find_needles_request],
        mock_gets=[
            MockGet(
                output_type=HydratedSources,
                input_type=HydrateSourcesRequest,
                mock=mock_hydrate_sources,
            )
        ],
    )
    assert list(result) == [tgt2]
