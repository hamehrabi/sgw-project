"""FTEST-001 — REQ-F-010. Defined in `03-tests/04-failure/failure-tests.md`.

A prepared storm valid for three of five inputs. Expect the load to fail **as a whole**, no
scenario row, every already-loaded scenario still working, and the failing file and stage
named. Log event `SCENARIO_PARSE_FAILED`.

"A half-loaded storm is worse than a refused one, because it looks complete"
(`technical-spec.md` §9.1). The parse is never retried automatically: a malformed file is a
fact about the file, not a transient error.
"""

import logging

from conftest import fixture_files, sign_in


def upload(client, files):
    return client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "prepared fixture"},
        files=[("files", (name, content, "text/csv")) for name, content in files.items()],
    )


def as_admin(client, accounts):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])


def broken_after_three_files():
    """Manifest, assets and maintenance are fine; weather is truncated mid-file."""
    files = fixture_files()
    files["weather.csv"] = b"grid_cell_id,asset_id,valid_time,wind_gust_mph,rainfall_in\nGC-01,"
    return files


def test_a_partial_parse_creates_no_scenario(client, application, accounts):
    as_admin(client, accounts)

    upload(client, broken_after_three_files())

    assert application.state.db.execute("select count(*) from scenarios").fetchone()[0] == 0
    assert application.state.db.execute("select count(*) from assets").fetchone()[0] == 0


def test_the_upload_is_recorded_as_failed_and_names_the_file(client, application, accounts):
    as_admin(client, accounts)

    upload(client, broken_after_three_files())

    row = application.state.db.execute(
        "select status, failed_file, scenario_id from scenario_uploads"
    ).fetchone()
    assert row["status"] == "failed"
    assert row["failed_file"] == "weather.csv"
    assert row["scenario_id"] is None


def test_the_failure_is_logged_by_name(client, accounts, caplog):
    caplog.set_level(logging.DEBUG)
    as_admin(client, accounts)

    upload(client, broken_after_three_files())

    assert any("SCENARIO_PARSE_FAILED" in record.getMessage() for record in caplog.records)


def test_an_already_loaded_scenario_survives_a_later_bad_load(client, application, accounts):
    """The one that matters: a bad upload must not disturb the storm already on screen."""
    as_admin(client, accounts)
    upload(client, fixture_files())
    before = application.state.db.execute("select count(*) from assets").fetchone()[0]
    assert before > 0

    upload(client, broken_after_three_files())

    after = application.state.db.execute("select count(*) from assets").fetchone()[0]
    assert after == before
    assert application.state.db.execute("select count(*) from scenarios").fetchone()[0] == 1


def test_a_manifest_row_count_that_disagrees_with_the_file_fails_the_load(
    client, application, accounts
):
    """The failure a size limit does not catch: a CSV that parses and is the wrong length."""
    as_admin(client, accounts)
    files = fixture_files()
    files["assets.csv"] = b"\n".join(files["assets.csv"].split(b"\n")[:4])

    upload(client, files)

    row = application.state.db.execute(
        "select status, failed_file from scenario_uploads"
    ).fetchone()
    assert row["status"] == "failed"
    assert row["failed_file"] == "assets.csv"
    assert application.state.db.execute("select count(*) from scenarios").fetchone()[0] == 0


def test_a_failure_midway_through_the_write_leaves_nothing(client, application, accounts):
    """`reliability-specification.md` §8: a scenario load is one transaction.

    Raised as a check at the TASK-002 review. FTEST-001's other cases fail during *parsing*,
    before a row is written — so none of them would notice if the write itself were not
    atomic. This one fails after the scenario row is inserted and before its assets are, the
    one window in which a half-loaded storm could exist.
    """
    as_admin(client, accounts)
    real = application.state.db

    class FailsWritingAssets:
        """Delegates everything, and dies on the asset insert. `sqlite3.Connection`'s
        attributes are read-only, so the seam has to be around it rather than inside it."""

        def __getattr__(self, name):
            return getattr(real, name)

        def executemany(self, sql, *args, **kwargs):
            if "insert into assets" in sql:
                raise RuntimeError("simulated write failure")
            return real.executemany(sql, *args, **kwargs)

    application.state.db = FailsWritingAssets()
    try:
        upload(client, fixture_files())
    finally:
        application.state.db = real

    assert real.execute("select count(*) from scenarios").fetchone()[0] == 0
    assert real.execute("select count(*) from assets").fetchone()[0] == 0


def test_two_scenarios_never_blend(client, application, accounts):
    """Every read is scoped by `scenario_id`; a missing scope is a correctness bug.

    Raised as a check at the TASK-002 review. ITEST-005 formalises this under TASK-009, which
    builds the switching; the scoping itself exists now, and two storms blended into one view
    would look entirely plausible.
    """
    as_admin(client, accounts)
    first = upload(client, fixture_files()).json()["scenario_id"]

    second_files = fixture_files()
    second_files["assets.csv"] = second_files["assets.csv"].replace(b"SS-1042", b"ZZ-0001")
    second = upload(client, second_files).json()["scenario_id"]

    assert first != second
    first_codes = {
        code
        for item in client.get(f"/api/v1/scenarios/{first}/assets").json()["items"]
        for code in item["external_ids"]
    }
    second_codes = {
        code
        for item in client.get(f"/api/v1/scenarios/{second}/assets").json()["items"]
        for code in item["external_ids"]
    }

    assert "SS-1042" in first_codes and "SS-1042" not in second_codes
    assert "ZZ-0001" in second_codes and "ZZ-0001" not in first_codes


def test_nothing_partial_is_left_on_disk(client, accounts, env):
    import pathlib

    as_admin(client, accounts)

    upload(client, broken_after_three_files())

    upload_dir = pathlib.Path(env["SCENARIO_UPLOAD_DIR"])
    stored = [p for p in upload_dir.rglob("*") if p.is_file()] if upload_dir.exists() else []
    assert stored == [], "a failed upload leaves no files behind"
