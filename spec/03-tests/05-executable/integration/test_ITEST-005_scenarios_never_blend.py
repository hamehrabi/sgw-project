"""ITEST-005 — REQ-F-010. Defined in `03-tests/02-functional/integration-tests.md`.

    Integration point:  API + database
    Scenario:           two scenarios loaded; request the ranking for one
    Expected result:    200, containing only that scenario's assets
    Side effect:        **zero rows from the other scenario in the response, at any page**

`security-review.md` §4 says why this row exists: *"a missing scope here is a correctness bug —
two storms blended into one ranking would look entirely plausible."* Nothing on the screen would
look wrong. That is the whole difficulty: this is the one defect in the product with no visible
symptom, so it has to be asserted rather than noticed.

**"At any page" is the clause that needed something built.** Until this task `GET /risks`
carried `limit` and no way to ask for a second page, so the clause could not be exercised at
all — a test reading the first page and stopping would have satisfied the row's wording and
proven nothing about the rest of the list. `api-specification.md` writes the endpoint out with a
`cursor` parameter and a `next_cursor` in the response; both are built here and both are used
below. The paging cases assert that **more than one page was needed**, because a `next_cursor`
that was always null would make every "no other storm's rows on page 2" assertion vacuous.

**Every assertion names both storms.** *Storm A's ranking contains none of storm B's assets* is
worth nothing without *storm B has assets*, and this repository has recorded four assertions
that could not have failed. So each test states the haystack — both storms loaded, both
non-empty, their asset sets disjoint — before it says anything about the needle.
"""

import pytest
from conftest import fixture_files, sign_in

# Two prepared storms with nothing in common: different assets, different grid cells, different
# forecast series. B carries three forecasts, which is what lets one storm's pointer be moved
# while the other's stays where it was.
STORM_A = "storm-with-seven-defects"
STORM_B = "storm-with-a-forecast-change"

# Written by every authenticated request, by design (ADR-006): the 240-minute idle limit is
# measured from `last_seen_at`. Excluded by name, never by a blanket.
HEARTBEAT_TABLE = "sessions"


def load(client, fixture, *, name, source_note) -> str:
    created = client.post(
        "/api/v1/scenarios",
        data={"name": name, "source_note": source_note},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files(fixture).items()],
    )
    assert created.status_code == 201, created.text
    return created.json()["scenario_id"]


@pytest.fixture
def two_storms(client, accounts):
    """Both loaded, both ranked, both non-empty, and no asset in common."""
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    a = load(client, STORM_A, name="Helene replay", source_note="NOAA 2024 replay pack")
    b = load(client, STORM_B, name="Track shift", source_note="Forecast-change rehearsal")

    assets_a = asset_ids(client, a)
    assets_b = asset_ids(client, b)
    # The haystack, once, for every test that takes this fixture.
    assert assets_a and assets_b, "a storm loaded with no assets proves nothing about scope"
    assert not (assets_a & assets_b), "the two fixtures share an asset id"
    return {"a": a, "b": b, "assets_a": assets_a, "assets_b": assets_b}


def asset_ids(client, scenario_id) -> set[str]:
    page = client.get(f"/api/v1/scenarios/{scenario_id}/assets")
    assert page.status_code == 200, page.text
    return {item["asset_id"] for item in page.json()["items"]}


def whole_ranking(client, scenario_id, *, limit, revision=None) -> tuple[list[str], int]:
    """Every page of one ranking, followed by the cursor the server hands back.

    Returns the asset ids in the order they were served and how many requests it took, so a
    caller can assert that paging actually happened rather than assuming it did.
    """
    collected: list[str] = []
    # The revision stays on every request, and the cursor is a page pointer rather than a
    # revision selector: a cursor that could change which ranking is being read would be the
    # silent substitution `technical-spec.md` §7.3 forbids, arriving through the other parameter.
    scope = "" if revision is None else f"&forecast_revision={revision}"
    query = f"?limit={limit}{scope}"
    pages = 0
    while True:
        page = client.get(f"/api/v1/scenarios/{scenario_id}/risks{query}")
        assert page.status_code == 200, page.text
        body = page.json()
        assert body["scenario_id"] == scenario_id
        collected.extend(item["asset_id"] for item in body["items"])
        pages += 1
        if body["next_cursor"] is None:
            return collected, pages
        assert pages < 50, "the cursor is not advancing"
        query = f"?limit={limit}{scope}&cursor={body['next_cursor']}"


def dump(connection) -> dict[str, list[tuple]]:
    """Every row of every table. "Nothing was written" is a claim about the database."""
    names = [
        row["name"]
        for row in connection.execute(
            "select name from sqlite_master where type = 'table'"
            " and name not like 'sqlite_%' order by name"
        )
    ]
    return {
        name: [tuple(row) for row in connection.execute(f"select * from {name}")]
        for name in names
    }


def assert_only_the_heartbeat_moved(before, after) -> None:
    assert set(before) == set(after), "a table appeared or vanished"
    for table, rows in before.items():
        if table == HEARTBEAT_TABLE:
            continue
        assert after[table] == rows, f"{table} was written to"


# --------------------------------------------------------------------------------------------
# The row itself: 200, containing only that scenario's assets.
# --------------------------------------------------------------------------------------------


def test_the_ranking_for_one_storm_carries_only_that_storms_assets(client, two_storms):
    served = client.get(f"/api/v1/scenarios/{two_storms['a']}/risks?limit=500")

    assert served.status_code == 200, served.text
    body = served.json()
    returned = {item["asset_id"] for item in body["items"]}
    # Both halves, and the pair is the point: the whole storm came back, and none of the other.
    assert returned == two_storms["assets_a"]
    assert not (returned & two_storms["assets_b"])
    assert body["total"] == len(two_storms["assets_a"])


def test_zero_rows_from_the_other_storm_on_any_page(client, two_storms):
    """The side effect ITEST-005 actually names, and the clause the endpoint had no way to
    answer until this task.

    A limit smaller than the storm, walked to the end. The page count is asserted because a
    server that answered every request with the whole list and a null cursor would satisfy every
    membership assertion below on a single page.
    """
    served, pages = whole_ranking(client, two_storms["a"], limit=3)

    assert pages >= 3, f"the ranking came back in {pages} page(s); paging was never exercised"
    assert set(served) == two_storms["assets_a"]
    assert not (set(served) & two_storms["assets_b"])
    # Each asset once. A page boundary that repeated or skipped a row would still satisfy a
    # set comparison, and a duplicated asset on a ranking is a second recommendation about it.
    assert len(served) == len(two_storms["assets_a"])


def test_paging_the_other_storm_is_the_other_storm_all_the_way_down(client, two_storms):
    """The same walk from the other end. One storm scoped correctly and the other not is the
    likelier bug than both being wrong, and a test that only ever pages storm A cannot see it."""
    served, pages = whole_ranking(client, two_storms["b"], limit=2)

    assert pages >= 2
    assert set(served) == two_storms["assets_b"]
    assert not (set(served) & two_storms["assets_a"])


def test_a_cursor_issued_for_one_storm_is_refused_by_the_other(client, two_storms):
    """The paging equivalent of `technical-spec.md` §7.3's rule about a forecast revision:
    **never a silent substitution.** A cursor is an offset into one storm's ranking at one
    revision; applied to another storm it would page a list the reader never asked for, and the
    response would look entirely ordinary. It is refused, and the refusal says which rule."""
    first = client.get(f"/api/v1/scenarios/{two_storms['a']}/risks?limit=3").json()
    assert first["next_cursor"], "storm A produced no second page to carry a cursor"

    crossed = client.get(
        f"/api/v1/scenarios/{two_storms['b']}/risks?limit=3&cursor={first['next_cursor']}"
    )

    assert crossed.status_code == 400
    assert set(crossed.json()) == {"code", "message"}
    # Read out of the message: `400` has more than one cause on this endpoint, and a cursor
    # refused for being unreadable is a different rule from one refused for naming another storm.
    assert "another storm" in crossed.json()["message"]
    # The haystack: the same cursor works on the storm it was issued for.
    assert (
        client.get(
            f"/api/v1/scenarios/{two_storms['a']}/risks?limit=3&cursor={first['next_cursor']}"
        ).status_code
        == 200
    )


def test_a_cursor_issued_for_one_revision_is_refused_by_another(client, two_storms):
    """Same rule, one axis over. Storm B carries three forecasts; a cursor into revision 0's
    order applied to revision 1 pages a different ranking under the same name — which is AC-005's
    *the previous order remains retrievable* quietly becoming *the previous order remains
    retrievable except after page one*."""
    applied = client.post(f"/api/v1/scenarios/{two_storms['b']}/forecast-revisions")
    assert applied.status_code == 201, applied.text
    first = client.get(
        f"/api/v1/scenarios/{two_storms['b']}/risks?limit=2&forecast_revision=0"
    ).json()
    assert first["next_cursor"]

    crossed = client.get(
        f"/api/v1/scenarios/{two_storms['b']}/risks"
        f"?limit=2&forecast_revision=1&cursor={first['next_cursor']}"
    )

    assert crossed.status_code == 400
    assert "revision" in crossed.json()["message"]
    # The haystack: revision 1 pages perfectly well from its own first page.
    assert (
        client.get(
            f"/api/v1/scenarios/{two_storms['b']}/risks?limit=2&forecast_revision=1"
        ).status_code
        == 200
    )


def test_a_page_boundary_inside_the_unscored_group_repeats_and_drops_nothing(
    client, two_storms, application
):
    """The tiebreak, and the reason it is not decoration.

    Every UNSCORED asset carries `rank is null`, so `order by rank is null, rank` leaves the
    whole unscored group in an order SQLite does not define — and an undefined order under
    `limit`/`offset` serves a row twice on one page and never on another. On a 220-asset storm
    with a handful of unscorable assets, which is exactly what FTEST-004 exists for, that is an
    asset silently missing from a ranking.

    **No shipped fixture can show it**: each of the three has exactly *one* unscored asset, so
    `rank is null, rank` is already total for them and removing `asset_id` changes nothing —
    `AGENT.md`'s row about a fixture where the coarse and the fine answers are the same number.
    So the rows are written directly, at a revision this storm carries and has not ranked, and
    **deliberately in an order that is not their asset-id order**: without the tiebreak the walk
    below comes back in the order they were inserted, which is a different list.
    """
    connection = application.state.db
    scenario_id = two_storms["b"]
    assets = sorted(two_storms["assets_b"])
    assert len(assets) >= 4, "too few assets to straddle a page boundary"

    # Revision 1 exists as a forecast and has no ranking yet, so this writes rather than rewrites
    # (CHG-026: a stored ranking is never rewritten, and the store enforces it).
    for position, asset_id in enumerate(reversed(assets)):
        connection.execute(
            "insert into risk_scores (id, scenario_id, asset_id, forecast_revision, score, band,"
            " rank, reasons, unscored_reason, weight_set_version, computed_at)"
            " values (?, ?, ?, 1, null, null, null, '[]', 'no gust for this cell', 'w1', ?)",
            (f"RS-unscored-{position}", scenario_id, asset_id, "2026-08-16T00:00:00Z"),
        )
    connection.commit()

    served, pages = whole_ranking(client, scenario_id, limit=2, revision=1)

    assert pages >= 3, f"the unscored group fitted in {pages} page(s); no boundary was crossed"
    # Each asset once — the assertion a repeated or skipped row breaks.
    assert len(served) == len(assets)
    assert sorted(served) == assets
    # And in the order the total key gives, which is not the order they were written in.
    assert served == assets
    assert served != list(reversed(assets))
    assert not (set(served) & two_storms["assets_a"])


def test_the_recommendation_records_the_whole_ranking_and_not_the_page(client, two_storms):
    """FF-005 and REQ-F-009, against the hazard paging introduces.

    The `recommendation` row exists so that *what was shown can be reconstructed later*, and what
    was delivered is the **ranking** — the whole list a reader is paging through. Built from the
    rows the handler happened to return, a reader who asked for two at a time would append an
    audit row naming two assets out of two hundred and twenty, and a decision recorded against it
    would be a decision about a list nobody can rebuild.

    Both halves: the row names every ranked asset, and it names none of the other storm's.
    """
    served = client.get(f"/api/v1/scenarios/{two_storms['a']}/risks?limit=2")

    assert served.status_code == 200, served.text
    body = served.json()
    assert len(body["items"]) == 2 < body["total"], "the page was not smaller than the ranking"

    record = client.get(f"/api/v1/scenarios/{two_storms['a']}/decisions").json()
    recommendations = [row for row in record["items"] if row["kind"] == "recommendation"]
    assert len(recommendations) == 1
    recorded = {entry["asset_id"] for entry in recommendations[0]["payload"]["ranked"]}
    assert recorded == two_storms["assets_a"]
    assert not (recorded & two_storms["assets_b"])


def test_an_unreadable_cursor_is_refused_rather_than_ignored(client, two_storms):
    """A cursor that cannot be decoded must not fall back to page one: a caller walking a list
    would silently restart it and read the same page forever, or — worse for this row — believe
    they had seen the whole storm."""
    refused = client.get(f"/api/v1/scenarios/{two_storms['a']}/risks?limit=3&cursor=not-a-cursor")

    assert refused.status_code == 400
    assert "cursor" in refused.json()["message"]


# --------------------------------------------------------------------------------------------
# Done criterion 3: every scenario-scoped read is scoped, not only the ranking.
# --------------------------------------------------------------------------------------------


def test_the_asset_view_carries_one_storm_and_not_the_other(client, two_storms):
    a = client.get(f"/api/v1/scenarios/{two_storms['a']}/assets").json()

    assert {item["asset_id"] for item in a["items"]} == two_storms["assets_a"]
    assert not ({item["asset_id"] for item in a["items"]} & two_storms["assets_b"])


def test_the_board_carries_one_storm_and_not_the_other(client, two_storms):
    """Both storms get a report, so neither board is empty — a board that returned nothing at
    all would pass a *no rows from the other storm* assertion perfectly."""
    filed_a = client.post(
        f"/api/v1/scenarios/{two_storms['a']}/damage-reports", json={"neighbourhood": "Northgate"}
    )
    filed_b = client.post(
        f"/api/v1/scenarios/{two_storms['b']}/damage-reports", json={"neighbourhood": "Southbank"}
    )
    assert filed_a.status_code == 201, filed_a.text
    assert filed_b.status_code == 201, filed_b.text

    board_a = client.get(f"/api/v1/scenarios/{two_storms['a']}/jobs").json()
    board_b = client.get(f"/api/v1/scenarios/{two_storms['b']}/jobs").json()

    assert board_a["job_count"] == 1 and board_b["job_count"] == 1
    assert [job["location"]["neighbourhood"] for job in board_a["items"]] == ["Northgate"]
    assert [job["location"]["neighbourhood"] for job in board_b["items"]] == ["Southbank"]
    ids_a = {report["report_id"] for job in board_a["items"] for report in job["reports"]}
    ids_b = {report["report_id"] for job in board_b["items"] for report in job["reports"]}
    assert ids_a and ids_b and not (ids_a & ids_b)


def test_the_decision_record_carries_one_storm_and_not_the_other(client, two_storms):
    """Delivering each ranking appends a `recommendation` row (FF-005), so both records are
    non-empty before either is read."""
    client.get(f"/api/v1/scenarios/{two_storms['a']}/risks")
    client.get(f"/api/v1/scenarios/{two_storms['b']}/risks")

    record_a = client.get(f"/api/v1/scenarios/{two_storms['a']}/decisions").json()
    record_b = client.get(f"/api/v1/scenarios/{two_storms['b']}/decisions").json()

    assert record_a["items"] and record_b["items"]
    ids_a = {row["id"] for row in record_a["items"]}
    ids_b = {row["id"] for row in record_b["items"]}
    assert not (ids_a & ids_b)
    for row in record_a["items"]:
        assert row["subject_id"].startswith(two_storms["a"])
    for row in record_b["items"]:
        assert row["subject_id"].startswith(two_storms["b"])


def test_each_storm_keeps_its_own_forecast_series_and_its_own_pointer(client, two_storms):
    """Storm B is moved to revision 1; storm A is not touched, and neither storm's forecast list
    grows the other's entries."""
    applied = client.post(f"/api/v1/scenarios/{two_storms['b']}/forecast-revisions")
    assert applied.status_code == 201, applied.text

    a = client.get(f"/api/v1/scenarios/{two_storms['a']}").json()
    b = client.get(f"/api/v1/scenarios/{two_storms['b']}").json()

    assert a["forecast_revision"] == 0
    assert b["forecast_revision"] == 1
    assert [e["forecast_revision"] for e in a["forecast_revisions"]] == [0]
    assert [e["forecast_revision"] for e in b["forecast_revisions"]] == [0, 1, 2]
    # And storm A's default ranking is still storm A's revision 0, not a 404 and not B's list.
    ranking = client.get(f"/api/v1/scenarios/{two_storms['a']}/risks?limit=500").json()
    assert ranking["forecast_revision"] == 0
    assert {item["asset_id"] for item in ranking["items"]} == two_storms["assets_a"]


# --------------------------------------------------------------------------------------------
# Done criterion 4: one storm's identifiers do not work against another storm.
# --------------------------------------------------------------------------------------------


def test_an_asset_from_the_other_storm_cannot_be_placed_against_this_one(client, two_storms):
    """The blend reached from a person's fingers. A crew recorded at an asset that is not in the
    storm on screen is a decision nobody can reconstruct, and `product-spec.md` §10 requires a
    placement to be traceable to the ranking it was made against."""
    theirs = sorted(two_storms["assets_b"])[0]

    refused = client.post(
        f"/api/v1/scenarios/{two_storms['a']}/placements",
        json={"crew": "North crew", "asset_ids": [theirs], "forecast_revision": 0, "note": None},
    )

    assert refused.status_code == 400
    # Which refusal, not merely that one happened: `400` has five causes on this endpoint.
    assert "not on this storm's ranking" in refused.json()["message"]
    # The haystack: the same call with one of this storm's own assets is accepted.
    mine = sorted(two_storms["assets_a"])[0]
    accepted = client.post(
        f"/api/v1/scenarios/{two_storms['a']}/placements",
        json={"crew": "North crew", "asset_ids": [mine], "forecast_revision": 0, "note": None},
    )
    assert accepted.status_code == 201, accepted.text


def test_an_asset_from_the_other_storm_cannot_be_named_on_a_damage_report(client, two_storms):
    theirs = sorted(two_storms["assets_b"])[0]

    refused = client.post(
        f"/api/v1/scenarios/{two_storms['a']}/damage-reports",
        json={"neighbourhood": "Northgate", "asset_id": theirs},
    )

    assert refused.status_code == 400
    assert "asset" in refused.json()["message"]
    mine = sorted(two_storms["assets_a"])[0]
    accepted = client.post(
        f"/api/v1/scenarios/{two_storms['a']}/damage-reports",
        json={"neighbourhood": "Northgate", "asset_id": mine},
    )
    assert accepted.status_code == 201, accepted.text


def test_a_recommendation_for_one_storm_is_not_decided_through_the_other(client, two_storms):
    """`decision_records` is where the blend would be permanent: a decision filed under storm A
    naming storm B's ranking cannot be corrected, only added to (BR-004)."""
    theirs = client.get(f"/api/v1/scenarios/{two_storms['b']}/risks").json()["recommendation_id"]
    mine = client.get(f"/api/v1/scenarios/{two_storms['a']}/risks").json()["recommendation_id"]
    assert theirs != mine

    decided = client.post(
        f"/api/v1/recommendations/{theirs}/decision", json={"decision": "accept", "note": None}
    )

    assert decided.status_code == 201, decided.text
    record_a = client.get(f"/api/v1/scenarios/{two_storms['a']}/decisions").json()
    record_b = client.get(f"/api/v1/scenarios/{two_storms['b']}/decisions").json()
    # The kind of a decision row is the decision itself — `accept`, `change` or `reject`
    # (`database-design.md` §3's enumeration), not the word "decision".
    kinds_a = [row["kind"] for row in record_a["items"]]
    kinds_b = [row["kind"] for row in record_b["items"]]
    assert "accept" in kinds_b
    assert "accept" not in kinds_a, "a decision about storm B landed in storm A's record"


# --------------------------------------------------------------------------------------------
# Done criteria 1 and 12: the list, and the fact that reading it changes nothing.
# --------------------------------------------------------------------------------------------


def test_the_list_names_every_loaded_storm_with_what_the_switcher_needs(client, two_storms):
    """`frontend-component-spec.md`: *loaded scenarios: name, source note, loaded date*.

    The source note is the one the admin typed. It used to be a SHA-256 digest, because the
    content key §5's idempotency rule turns on had no column of its own (CHG-031).
    """
    listed = client.get("/api/v1/scenarios")

    assert listed.status_code == 200, listed.text
    body = listed.json()
    by_id = {item["scenario_id"]: item for item in body["items"]}
    assert set(by_id) == {two_storms["a"], two_storms["b"]}
    assert body["total"] == 2

    assert by_id[two_storms["a"]]["name"] == "Helene replay"
    assert by_id[two_storms["a"]]["source_note"] == "NOAA 2024 replay pack"
    assert by_id[two_storms["b"]]["name"] == "Track shift"
    assert by_id[two_storms["b"]]["source_note"] == "Forecast-change rehearsal"
    for item in body["items"]:
        assert item["loaded_at"]
        assert item["ranked"] is True

    # **The count is this storm's, and the three answers differ** — `AGENT.md`'s row about a
    # figure that claims a resolution and is checked where every resolution gives the same
    # number. Storm A holds 7 assets — its eight records include the two codes for one
    # substation, joined into one row — storm B holds 5, and the database holds 12. A count that
    # forgot its `where scenario_id = ?` would read 12 beside both names, and a switcher saying
    # every storm has the same number of assets is a switcher nobody would question.
    assert by_id[two_storms["a"]]["asset_count"] == len(two_storms["assets_a"]) == 7
    assert by_id[two_storms["b"]]["asset_count"] == len(two_storms["assets_b"]) == 5
    assert sum(item["asset_count"] for item in body["items"]) == 12
    # Newest first, so the switcher's default is the storm somebody just loaded.
    assert [item["scenario_id"] for item in body["items"]] == [two_storms["b"], two_storms["a"]]


def test_the_list_says_which_storms_have_an_order_behind_them(client, two_storms, application):
    """CHG-027's argument, one component over: *a screen that must tell two things apart needs
    two things in the response.*

    A storm whose current revision has no ranking is one click from an empty screen, and an
    empty screen in this product reads as safety. `ranked` is read from the **stored rankings**
    and not from the pointer, which is the same distinction `GET /scenarios/{id}` had to make —
    so the disagreement is produced by moving the pointer directly, because that is the only way
    to make the two answers differ.
    """
    connection = application.state.db
    connection.execute(
        "update scenarios set forecast_revision = 2 where id = ?", (two_storms["b"],)
    )
    connection.commit()

    listed = {item["scenario_id"]: item for item in client.get("/api/v1/scenarios").json()["items"]}

    # Both halves: the storm with an order says so, and the storm without one does not.
    assert listed[two_storms["a"]]["ranked"] is True
    assert listed[two_storms["b"]]["ranked"] is False
    assert listed[two_storms["b"]]["forecast_revision"] == 2
    # And the storm reporting `false` reports it truthfully.
    assert client.get(f"/api/v1/scenarios/{two_storms['b']}/risks").status_code == 404
    assert client.get(f"/api/v1/scenarios/{two_storms['a']}/risks").status_code == 200


def test_the_list_carries_no_asset_and_no_location(client, two_storms):
    """CON-003 and REQ-NF-007. A list of storms is a count and nothing finer — no asset id, no
    coordinate, no neighbourhood — and this is the cheapest place for one to be added by
    accident, because a switcher showing "3 substations at risk" would look helpful."""
    body = client.get("/api/v1/scenarios").json()

    text = repr(body)
    for asset_id in two_storms["assets_a"] | two_storms["assets_b"]:
        assert asset_id not in text
    for forbidden in ("lat", "lon", "neighbourhood", "location", "external_ids"):
        assert forbidden not in text


def test_both_roles_may_read_the_list(client, accounts, two_storms):
    """`technical-spec.md` §7.2: *Switch between loaded scenarios — Admin yes, User yes.* The
    deny path is STEST-001's; the allow path is here, because implementing a permission's allow
    path and not its deny path is one of `AGENT.md`'s three predicted failures and this is the
    other half of it."""
    client.delete("/api/v1/auth/session")
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])

    listed = client.get("/api/v1/scenarios")

    assert listed.status_code == 200, listed.text
    assert {item["scenario_id"] for item in listed.json()["items"]} == {
        two_storms["a"],
        two_storms["b"],
    }


def test_switching_between_storms_writes_nothing(client, two_storms, application):
    """A switch is a read. No storm is marked current, none is archived, and nothing about the
    one being left changes because somebody looked elsewhere."""
    # Deliver both rankings first, so FF-005's `recommendation` rows already exist and *nothing
    # was written* is exact rather than approximately true.
    client.get(f"/api/v1/scenarios/{two_storms['a']}/risks")
    client.get(f"/api/v1/scenarios/{two_storms['b']}/risks")
    connection = application.state.db
    before = dump(connection)
    assert before["scenarios"] and before["risk_scores"] and before["decision_records"]
    assert len(before["scenarios"]) == 2

    client.get("/api/v1/scenarios")
    client.get(f"/api/v1/scenarios/{two_storms['b']}")
    client.get(f"/api/v1/scenarios/{two_storms['b']}/risks")
    client.get(f"/api/v1/scenarios/{two_storms['a']}")
    client.get(f"/api/v1/scenarios/{two_storms['a']}/risks")

    assert_only_the_heartbeat_moved(before, dump(connection))


def test_the_dump_notices_a_write_when_one_happens(client, two_storms, application):
    """The positive assertion beside the negative one: a dump that had stopped returning rows
    would satisfy every comparison above."""
    connection = application.state.db
    before = dump(connection)

    filed = client.post(
        f"/api/v1/scenarios/{two_storms['a']}/damage-reports", json={"neighbourhood": "Northgate"}
    )

    assert filed.status_code == 201, filed.text
    after = dump(connection)
    assert after != before
    assert len(after["damage_reports"]) == len(before["damage_reports"]) + 1


def test_loading_the_same_storm_twice_leaves_one_entry_in_the_list(client, two_storms):
    """§5: *an identical re-load replaces in place rather than creating a rival ranking.* Two
    entries for one storm is the switcher asking a person to choose between a thing and itself,
    and the second one would carry its own ranking for the same weather."""
    again = client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay again", "source_note": "a different note entirely"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files(STORM_A).items()],
    )

    assert again.status_code == 200, again.text
    assert again.json()["scenario_id"] == two_storms["a"]
    listed = client.get("/api/v1/scenarios").json()
    assert len(listed["items"]) == 2
