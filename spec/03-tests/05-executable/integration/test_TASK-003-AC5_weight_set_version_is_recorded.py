"""TASK-003 acceptance criterion 5 — defined in `02-tasks/02-task-files/TASK-003.md`.

"Every stored ranking records the weight-set version that produced it, so a later
recalibration does not silently rewrite history."

Raised as a check at the TASK-003 review. No `TEST-` identifier is cited because the register
defines none — the criterion comes from the task, and minting an id here would create one
`unit-tests.md` does not own.

**This is the criterion the weights exist to make survivable.** ADR-007's numbers are an
assumption awaiting calibration with SGW's engineers; the whole point of expecting them to
change is that a rank produced under the old numbers must still be able to say so. A ranking
that cannot name its own weight set is a ranking nobody can re-derive, and auditability is a
driving characteristic.
"""

from conftest import fixture_files, sign_in


def load(client, accounts):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    return created.json()["scenario_id"]


def test_the_version_is_stored_on_every_row(client, application, accounts):
    load(client, accounts)

    versions = {
        row["weight_set_version"]
        for row in application.state.db.execute("select weight_set_version from risk_scores")
    }

    from app.scoring.references import WEIGHT_SET_VERSION

    assert versions == {WEIGHT_SET_VERSION}


def test_the_column_refuses_a_row_without_one(client, application, accounts):
    """`not null` in the schema, not a default in code — the store is the enforcement."""
    import sqlite3

    import pytest

    scenario_id = load(client, accounts)
    asset_id = application.state.db.execute(
        "select id from assets where scenario_id = ?", (scenario_id,)
    ).fetchone()["id"]

    with pytest.raises(sqlite3.IntegrityError):
        application.state.db.execute(
            "insert into risk_scores (id, scenario_id, asset_id, forecast_revision, score,"
            " rank, reasons, weight_set_version, computed_at)"
            " values ('R-X', ?, ?, 9, 10.0, 1, '[{\"factor\":\"flood_zone\"}]', NULL, 'now')",
            (scenario_id, asset_id),
        )
        application.state.db.commit()


def test_the_version_reaches_the_api_so_a_reader_can_see_it(client, accounts):
    scenario_id = load(client, accounts)

    body = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()

    from app.scoring.references import WEIGHT_SET_VERSION

    assert body["weight_set_version"] == WEIGHT_SET_VERSION
    assert all(item["weight_set_version"] == WEIGHT_SET_VERSION for item in body["items"])


def test_recalibrating_does_not_rewrite_what_was_already_stored(client, application, accounts):
    """The point of the criterion, demonstrated rather than asserted.

    A ranking written under one version must still say that version after the weights
    are changed. If the version were derived at read time from current configuration instead of
    stored at write time, this passes silently today and quietly rewrites history the first
    time anyone calibrates.
    """
    scenario_id = load(client, accounts)
    before = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()

    from app.scoring import references

    original = references.WEIGHT_SET_VERSION
    try:
        references.WEIGHT_SET_VERSION = "sgw-calibrated-v2"
        after = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    finally:
        references.WEIGHT_SET_VERSION = original

    assert after["weight_set_version"] == original
    assert after["items"] == before["items"], "a stored ranking must not change under its feet"
