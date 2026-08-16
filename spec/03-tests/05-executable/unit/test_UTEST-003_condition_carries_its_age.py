"""UTEST-003 — REQ-F-001. Defined in `03-tests/02-functional/unit-tests.md`.

Defect 2 — condition data is old, between two months and six years back.
  normal  — an inspection dated 2 months ago carries its date
  edge    — an inspection dated 6 years ago still loads, carrying its date
  failure — a condition stored with no `condition_observed_at` → refused by the store

The failure case is asserted against the **database**, not the loader. BR-003's check
constraint is in `database-design.md` §3, and a loader that happened to be careful would
pass a service-layer version of this test while the constraint was missing.
"""

import sqlite3

import pytest
from conftest import fixture_files


def load():
    from app.loader.load import load_scenario

    return load_scenario(fixture_files())


def find(assets, external_id):
    return next(a for a in assets if external_id in a.external_ids)


def test_a_recent_inspection_carries_its_date():
    result = load()

    eastbank = find(result.assets, "SS-5566")

    assert eastbank.condition == "4"
    assert eastbank.condition_observed_at == "2026-07-15"
    assert eastbank.condition_source


def test_a_six_year_old_inspection_still_loads_carrying_its_date():
    """Old is not missing. Dropping it would lose the input §7 worked hardest to obtain."""
    result = load()

    delta = find(result.assets, "PL-7788")

    assert delta.condition == "1"
    assert delta.condition_observed_at == "2019-02-28"


def test_an_asset_with_no_condition_loads_with_none_rather_than_a_default():
    """A missing condition must not become a good one, or a bad one."""
    result = load()

    coastal = find(result.assets, "LN-8899")

    assert coastal.condition is None
    assert coastal.condition_observed_at is None


def test_the_store_refuses_a_condition_without_its_age(application, accounts):
    connection = application.state.db
    connection.execute(
        # `content_key` and `seq` are required by migration 013: a storm is identified by
        # what it was loaded from, and has a place in the order storms are listed in
        # (CHG-031, CHG-032). A direct insert has to satisfy the store like any other.
        "insert into scenarios (id, name, source_note, content_key, loaded_by, loaded_at,"
        " forecast_revision, seq)"
        " values ('SC-1', 'S', 'n', ?, ?, '2026-08-15', 0, 900)",
        ("e" * 64, accounts["admin"]["id"]),
    )

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "insert into assets (id, scenario_id, external_ids, type, location, condition,"
            " condition_source, condition_observed_at, match_status, created_at)"
            " values ('A-1', 'SC-1', '[\"SS-1\"]', 'substation', '{}', '3',"
            " NULL, NULL, 'matched', '2026-08-15')"
        )
        connection.commit()


def test_the_store_accepts_a_condition_that_carries_source_and_age(application, accounts):
    connection = application.state.db
    connection.execute(
        # `content_key` and `seq` are required by migration 013: a storm is identified by
        # what it was loaded from, and has a place in the order storms are listed in
        # (CHG-031, CHG-032). A direct insert has to satisfy the store like any other.
        "insert into scenarios (id, name, source_note, content_key, loaded_by, loaded_at,"
        " forecast_revision, seq)"
        " values ('SC-1', 'S', 'n', ?, ?, '2026-08-15', 0, 900)",
        ("e" * 64, accounts["admin"]["id"]),
    )

    connection.execute(
        "insert into assets (id, scenario_id, external_ids, type, location, condition,"
        " condition_source, condition_observed_at, match_status, created_at)"
        " values ('A-1', 'SC-1', '[\"SS-1\"]', 'substation', '{}', '3',"
        " 'inspection', '2026-06-02', 'matched', '2026-08-15')"
    )
    connection.commit()

    assert connection.execute("select count(*) from assets").fetchone()[0] == 1
