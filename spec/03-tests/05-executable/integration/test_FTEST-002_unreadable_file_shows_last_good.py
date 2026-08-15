"""FTEST-002 — REQ-NF-003(b). Defined in `03-tests/04-failure/failure-tests.md`.

A prepared data file becomes unreadable after load. **Consequence corrected by CHG-013.**

The joined view is served from stored rows (`technical-spec.md` §6), so a lost source file
cannot reach it — the screen stays *correct*, not merely non-empty, and degrading it to a
"last good picture" would be a lie in the safe direction. What the loss does break is replay
(`outages.csv` is `ai-evals.md`'s input) and recovery (`technical-spec.md` §12 defines a
backup as the database **plus** the uploaded files), so it is named to an admin instead.

This file therefore asserts two things the old wording conflated: that the view is unaffected,
**and** that the loss is not silent.
"""

import pathlib

from conftest import fixture_files, sign_in


def load_as_admin(client, accounts):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    return created.json()["scenario_id"]


def remove_a_source_file(env, name="weather.csv"):
    upload_dir = pathlib.Path(env["SCENARIO_UPLOAD_DIR"])
    target = next(upload_dir.rglob(name))
    target.unlink()
    return name


def test_the_joined_view_is_unchanged_by_a_lost_source_file(client, accounts, env):
    scenario_id = load_as_admin(client, accounts)
    before = client.get(f"/api/v1/scenarios/{scenario_id}/assets").json()

    remove_a_source_file(env)

    after = client.get(f"/api/v1/scenarios/{scenario_id}/assets").json()
    assert after == before, "reads are served from stored rows; a lost file cannot reach them"


def test_no_screen_goes_blank_or_errors(client, accounts, env):
    scenario_id = load_as_admin(client, accounts)
    remove_a_source_file(env)

    for path in (f"/api/v1/scenarios/{scenario_id}", f"/api/v1/scenarios/{scenario_id}/assets"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json()


def test_the_loss_is_named_rather_than_silent(client, accounts, env):
    scenario_id = load_as_admin(client, accounts)
    missing = remove_a_source_file(env)

    body = client.get(f"/api/v1/scenarios/{scenario_id}").json()

    assert body["integrity"]["intact"] is False
    assert missing in body["integrity"]["missing_files"]


def test_the_notice_says_what_the_loss_actually_costs(client, accounts, env):
    """Not "your data is stale" — it is not. Replay and recovery are what break."""
    scenario_id = load_as_admin(client, accounts)

    remove_a_source_file(env)

    assert client.get(f"/api/v1/scenarios/{scenario_id}").json()["integrity"]["affects"] == [
        "replay",
        "recovery",
    ]


def test_losing_a_file_does_not_change_whether_the_data_is_stale(client, accounts, env):
    """The two are independent, and the first draft of this test conflated them.

    Asserting `stale is False` after removing a file passes or fails on the *fixture's* age —
    its forecast is issued a day before the fixture's own date, so it is legitimately stale
    and the assertion failed for a reason that had nothing to do with the file. Comparing
    before against after isolates the one variable this test is about.
    """
    scenario_id = load_as_admin(client, accounts)
    before = client.get(f"/api/v1/scenarios/{scenario_id}").json()["stale"]

    remove_a_source_file(env)

    after = client.get(f"/api/v1/scenarios/{scenario_id}").json()["stale"]
    assert after == before, "staleness is the age of the data, not the presence of a file"


def test_an_intact_scenario_reports_itself_intact(client, accounts):
    """The control. Without it the notice could be permanently on and still pass."""
    scenario_id = load_as_admin(client, accounts)

    body = client.get(f"/api/v1/scenarios/{scenario_id}").json()

    assert body["integrity"]["intact"] is True
    assert body["integrity"]["missing_files"] == []


def test_every_missing_file_is_named_not_just_the_first(client, accounts, env):
    scenario_id = load_as_admin(client, accounts)
    remove_a_source_file(env, "weather.csv")
    remove_a_source_file(env, "outages.csv")

    named = client.get(f"/api/v1/scenarios/{scenario_id}").json()["integrity"]["missing_files"]

    assert sorted(named) == ["outages.csv", "weather.csv"]
