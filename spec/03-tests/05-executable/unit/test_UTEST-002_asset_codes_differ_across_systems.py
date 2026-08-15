"""UTEST-002 — REQ-F-001. Defined in `03-tests/02-functional/unit-tests.md`.

Defect 1 — the same asset carries different codes in different systems.
  normal  — `SS-1042` and `TX-4471` matched by the join key → one asset
  edge    — a near-match below the confidence bar → `needs_review`, not merged
  failure — a merge performed on a guess → test fails

**The join key is not fixed by the specification**, and this test is where the choice is
written down: same `type`, same location to four decimal places (~11 m), and the same
normalised name. Coordinates and type alone are a *near* match — the fixture's two harbour
pumps share both and are different assets — so a name that disagrees withholds the merge
rather than completing it. Never merge on a guess (AC-001).
"""

from conftest import fixture_files


def load():
    from app.loader.load import load_scenario

    return load_scenario(fixture_files())


def find(assets, external_id):
    return next(a for a in assets if external_id in a.external_ids)


def test_two_codes_for_one_substation_become_one_asset():
    result = load()

    northgate = find(result.assets, "SS-1042")

    assert sorted(northgate.external_ids) == ["SS-1042", "TX-4471"]
    assert northgate.match_status == "matched"


def test_the_merged_asset_appears_exactly_once():
    result = load()

    appearances = [a for a in result.assets if "SS-1042" in a.external_ids]

    assert len(appearances) == 1
    assert sum("TX-4471" in a.external_ids for a in result.assets) == 1


def test_a_near_match_is_flagged_rather_than_merged():
    """Same coordinates, same type, names that do not agree. Two pumps, not one."""
    result = load()

    harbor = find(result.assets, "SS-2210")
    harbour = find(result.assets, "PS-9001")

    assert harbor is not harbour, "a near match must never be merged on a guess"
    assert harbor.match_status == "needs_review"
    assert harbour.match_status == "needs_review"


def test_an_unmatchable_record_is_surfaced_never_dropped():
    """Omitting the row would be the tidiest code and the most dangerous screen."""
    result = load()

    flagged = [a for a in result.assets if a.match_status == "needs_review"]

    assert flagged, "records the join could not resolve must reach a person"
    assert all(a.external_ids for a in result.assets)


def test_every_asset_in_the_file_is_accounted_for():
    result = load()

    ids = {code for asset in result.assets for code in asset.external_ids}

    assert ids == {
        "SS-1042", "TX-4471", "SS-2210", "PS-9001",
        "LN-3312", "SS-5566", "PL-7788", "LN-8899",
    }
