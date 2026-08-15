"""UTEST-008 — REQ-F-001. Defined in `03-tests/02-functional/unit-tests.md`.

Defects 6 and 7 — repair records are not failure records; public data is county-level.
  normal  — failures taken only from outage records
  edge    — a routine work order present → excluded from the failure set
  failure — a failure list derived from repair logs → test fails

Defect 6 is the subtle one. `maintenance.csv` is full of rows that look like failures — the
fixture's `LN-3312` row says REPAIR ORDER and describes replacing hardware — and counting
them would inflate the failure history with scheduled work. The failure set comes from
`outages.csv` and from nowhere else.

Defect 7 is a recorded ceiling rather than a behaviour: public outage data is area-level and
never names the failed asset. The loader must keep such a row without inventing an asset for
it, which is what the fixture's blank `asset_id` row is for.
"""

from conftest import fixture_files


def load():
    from app.loader.load import load_scenario

    return load_scenario(fixture_files())


def test_the_failure_set_comes_from_the_outage_file():
    result = load()

    assert result.failures
    assert all(failure.source_file == "outages.csv" for failure in result.failures)


def test_a_repair_order_in_the_maintenance_file_is_not_a_failure():
    result = load()

    subjects = {failure.asset_external_id for failure in result.failures}

    # LN-3312's only appearance is a maintenance REPAIR ORDER. It never failed.
    assert "LN-3312" not in subjects


def test_no_failure_is_derived_from_maintenance_at_all():
    result = load()

    maintenance_only = {"LN-3312"}
    outage_backed = {failure.asset_external_id for failure in result.failures}

    assert not (outage_backed & maintenance_only)


def test_an_area_level_outage_loads_without_inventing_an_asset():
    """Defect 7. A report with no matching asset is still a report (§4)."""
    result = load()

    unattributed = [o for o in result.outages if o.asset_external_id is None]

    assert unattributed, "an area-level row must survive the load"
    assert unattributed[0].service_area_id == "SA-NORTH"


def test_both_defects_are_recorded_as_caught():
    result = load()

    caught = {finding.defect for finding in result.findings}

    assert 6 in caught
    assert 7 in caught


def test_an_inspection_note_is_not_mistaken_for_a_repair_record():
    """Defect 6's check matched "routine" and "scheduled", so an inspection tripped it.

    "Routine inspection - no action" is an inspection. Counting it as repair work made the
    check fire on every dataset that contains an inspection — which is every dataset — so it
    reported defect 6 whether or not repair records were present. Found by removing each
    defect from the fixture in turn during the TASK-002 review.
    """
    from app.loader.defects import looks_like_scheduled_work

    assert looks_like_scheduled_work("Routine inspection - no action") is False
    assert looks_like_scheduled_work("Seals degraded; scheduled for replacement") is False
    assert looks_like_scheduled_work("Corrosion noted on intake housing") is False
    assert looks_like_scheduled_work("REPAIR ORDER - replaced insulator string") is True
    assert looks_like_scheduled_work("Work order 4471: repaired the breaker") is True


def test_all_seven_defects_are_caught_by_their_own_check():
    """FF-006's threshold, asserted here as well as in the gate: 7 of 7.

    "By its **own** check" is the load-bearing phrase, and it is not provable from this
    assertion alone — seven findings could come from five checks, two of which fire on any
    dataset. The review runs the complement: remove each defect from the fixture in turn and
    require the matching finding to disappear. Two checks failed that in TASK-002 and are
    pinned by the two tests above.
    """
    result = load()

    assert {finding.defect for finding in result.findings} == {1, 2, 3, 4, 5, 6, 7}
