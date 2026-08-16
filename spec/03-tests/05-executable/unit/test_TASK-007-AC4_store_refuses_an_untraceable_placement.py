"""TASK-007 done criteria 4, 5 and 6 — the store refuses a placement it cannot trace.

**Every statement here is issued directly against the database.** The endpoint is the thing
being tested elsewhere; it is not the guarantee. `review-log.md` carries a standing **Block**
condition — *a rule enforced in the service layer that the store could refuse* — and it has
fired twice, once on `damage_reports.asset_id` proving existence rather than membership
(CHG-019) and once on a `unique` constraint that could not see the normalisation in front of it
(CHG-023). Both were found by asking *what can a direct insert put in that column*, and that is
the only question this file asks.

`product-spec.md` §10 says a placement is *"traceable to the ranking and forecast revision it was
made against"*. That is not a sentence about the response body: it is a property of the stored
row, and the store is where it is held (CHG-029, migration 012).

**Each refusal is read out of the message**, because five of this repository's assertions have
turned out to pass for a rule other than the one they named — the most recent when a new insert
guard made UTEST-009 stop testing BR-002 without changing a line of it.

**And the positive case comes first in every group.** An enumeration that refuses everything
would satisfy every negative below and prove nothing (`AGENT.md`'s fourth lessons row).
"""

import json
import re
import sqlite3

import pytest
from app.store import blanks, decisions
from conftest import fixture_files, sign_in

FIXTURE = "storm-for-the-planning-flow"

AT_THE_LIMIT = "C" * decisions.CREW_LABEL_MAX
OVER_THE_LIMIT = "C" * (decisions.CREW_LABEL_MAX + 1)


def load(client, accounts, name="Planning flow", fixture=FIXTURE) -> str:
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": name, "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files(fixture).items()],
    )
    assert created.status_code == 201, created.text
    scenario_id = created.json()["scenario_id"]
    # The ranking has to be delivered for the `recommendation` row to exist; the rankings
    # themselves are written at load, which is what the trigger reads.
    client.get(f"/api/v1/scenarios/{scenario_id}/risks")
    return scenario_id


def ranked_assets(connection, scenario_id, forecast_revision=0) -> list[str]:
    return [
        row[0]
        for row in connection.execute(
            "select asset_id from risk_scores where scenario_id = ? and forecast_revision = ?"
            " order by rank is null, rank",
            (scenario_id, forecast_revision),
        )
    ]


def payload(asset_ids, *, crew="North crew", forecast_revision=0, note=None, **extra) -> str:
    body = {
        "crew": crew,
        "asset_ids": list(asset_ids),
        "forecast_revision": forecast_revision,
        "recommendation_id": None,
        "note": note,
    }
    body.update(extra)
    return json.dumps(body)


def insert(connection, scenario_id, actor, body, *, row_id="DR-direct", subject_id=None,
           subject_type="ranking", kind="placement"):
    """One placement, written the way nothing in `backend/` writes one."""
    revision = json.loads(body).get("forecast_revision")
    connection.execute(
        "insert into decision_records"
        " (id, scenario_id, occurred_at, actor_user_id, kind, subject_type, subject_id, payload)"
        " values (?, ?, '2026-08-16T00:00:00Z', ?, ?, ?, ?, ?)",
        (
            row_id,
            scenario_id,
            actor,
            kind,
            subject_type,
            f"{scenario_id}:{revision}" if subject_id is None else subject_id,
            body,
        ),
    )
    connection.commit()


def refusal(connection, *args, **kwargs) -> str:
    with pytest.raises(sqlite3.IntegrityError) as refused:
        insert(connection, *args, **kwargs)
    connection.rollback()
    return str(refused.value)


def test_a_well_formed_placement_is_accepted_by_a_direct_insert(client, accounts, application):
    """The haystack. Everything below is *this row, with one thing wrong*, and a store that
    refused all placements would pass every one of them."""
    connection = application.state.db
    scenario_id = load(client, accounts)
    assets = ranked_assets(connection, scenario_id)
    assert len(assets) >= 2, "the fixture ranked fewer than two assets"

    insert(connection, scenario_id, accounts["user"]["id"], payload(assets[:2]))

    stored = connection.execute(
        "select payload from decision_records where id = 'DR-direct'"
    ).fetchone()
    assert json.loads(stored["payload"])["asset_ids"] == assets[:2]


def test_an_asset_that_is_not_on_that_ranking_is_refused(client, accounts, application):
    """Traceability, as something the database will not accept.

    Not *"the asset exists"* — that is the foreign key CHG-019 showed proves nothing about
    membership. This is *"the asset is on the list this placement claims to have been made
    against"*, which is the claim `product-spec.md` §10 makes.
    """
    connection = application.state.db
    scenario_id = load(client, accounts)
    assets = ranked_assets(connection, scenario_id)

    message = refusal(
        connection, scenario_id, accounts["user"]["id"], payload([assets[0], "AS-invented"])
    )

    assert "only assets on the ranking" in message


def test_an_asset_from_another_storm_is_refused(client, accounts, application):
    """CHG-019's shape, on caller-supplied input, in the place it would next appear.

    The other storm's asset **exists**, and a check that only proved existence would accept it —
    which is precisely how a storm-A damage report came to be able to name storm-B's asset.
    """
    connection = application.state.db
    first = load(client, accounts)
    second = load(client, accounts, name="Helene replay", fixture="storm-with-seven-defects")
    theirs = ranked_assets(connection, second)
    assert theirs, "the second storm ranked nothing, so 'another storm's asset' is vacuous"
    assert connection.execute(
        "select count(*) from assets where id = ?", (theirs[0],)
    ).fetchone()[0] == 1, "the asset does not exist at all, so existence is not what is refused"

    message = refusal(connection, first, accounts["user"]["id"], payload([theirs[0]]))

    assert "only assets on the ranking" in message


def test_a_revision_this_storm_has_never_ranked_is_refused(client, accounts, application):
    """The asset is right and the revision is not. Recording a placement against a list that was
    never computed makes `subject_id` name a ranking nobody can read back."""
    connection = application.state.db
    scenario_id = load(client, accounts)
    assets = ranked_assets(connection, scenario_id)

    message = refusal(
        connection,
        scenario_id,
        accounts["user"]["id"],
        payload(assets[:1], forecast_revision=7),
    )

    assert "only assets on the ranking" in message


def test_a_placement_naming_no_asset_at_all_is_refused(client, accounts, application):
    """*Which crews wait where* — a placement with no `where` is a row that says a crew exists."""
    connection = application.state.db
    scenario_id = load(client, accounts)

    message = refusal(connection, scenario_id, accounts["user"]["id"], payload([]))

    assert "at least one asset" in message


def test_a_placement_naming_more_assets_than_the_bound_is_refused(client, accounts, application):
    """The other end of the same clause, written because nothing else reaches it.

    An unbounded list in a `json` column is the same shape as an unbounded upload, and the
    argument for a limit is the one `database-design.md`'s addendum makes about file size: a
    legitimate placement never comes near it and an unbounded payload cannot pass. The list is
    made of invented ids so the clause under test is the **count** — clause 2 aborts before the
    membership clause is ever consulted, which is the order the trigger is written in.
    """
    connection = application.state.db
    scenario_id = load(client, accounts)

    message = refusal(
        connection,
        scenario_id,
        accounts["user"]["id"],
        payload([f"AS-{index}" for index in range(501)]),
    )

    assert "no more than 500" in message


def test_a_placement_naming_one_asset_twice_is_refused(client, accounts, application):
    """A crew waits at a place once. Two entries would double it in every count built on this
    row, and the count is the only thing anyone will ever aggregate here."""
    connection = application.state.db
    scenario_id = load(client, accounts)
    assets = ranked_assets(connection, scenario_id)

    message = refusal(
        connection, scenario_id, accounts["user"]["id"], payload([assets[0], assets[0]])
    )

    assert "each asset once" in message


@pytest.mark.parametrize(
    "label",
    [
        pytest.param("", id="empty"),
        pytest.param("   ", id="spaces only"),
        pytest.param("\t\n", id="tab and newline only — SQLite's trim() strips neither"),
        pytest.param(" North crew", id="a leading space"),
        pytest.param("North crew ", id="a trailing space"),
        pytest.param("North\tcrew", id="a tab inside"),
        pytest.param("North\ncrew", id="a newline inside"),
        pytest.param("North\rcrew", id="a carriage return inside"),
        pytest.param(OVER_THE_LIMIT, id="one character over the bound"),
    ],
)
def test_a_crew_label_that_is_not_a_label_is_refused(client, accounts, application, label):
    """Every clause of the crew check, one case per clause.

    `AGENT.md`'s last lessons row is why the whitespace cases are enumerated rather than
    represented by one: writing them for `damage_reports.location` found that
    `length(trim(...)) between 1 and 120` **accepted** `"\\t\\n"` and refused `"   "`, because
    SQLite's `trim()` strips spaces and nothing else. The same clause, written the same way,
    would have the same hole. It does not, and these are the cases that say so.
    """
    connection = application.state.db
    scenario_id = load(client, accounts)
    assets = ranked_assets(connection, scenario_id)

    message = refusal(
        connection, scenario_id, accounts["user"]["id"], payload(assets[:1], crew=label)
    )

    assert "crew display label" in message


def test_a_crew_label_at_the_bound_is_accepted(client, accounts, application):
    """The permitted case beside the refused one. `OVER_THE_LIMIT` failing means nothing if
    `AT_THE_LIMIT` fails too — that would be a store that refuses long labels, not one that
    holds a bound."""
    connection = application.state.db
    scenario_id = load(client, accounts)
    assets = ranked_assets(connection, scenario_id)

    insert(
        connection, scenario_id, accounts["user"]["id"], payload(assets[:1], crew=AT_THE_LIMIT)
    )

    stored = connection.execute(
        "select payload from decision_records where id = 'DR-direct'"
    ).fetchone()
    assert json.loads(stored["payload"])["crew"] == AT_THE_LIMIT


def test_one_bound_governs_the_crew_label(client, accounts, application):
    """Done criterion 5, and CHG-023's lesson applied before it bites rather than after.

    120 is written in the trigger and in `decisions.CREW_LABEL_MAX`. Nothing ties two hard-coded
    copies of one number together, and when they drift the endpoint's specified
    `400 validation_error` becomes a `500 internal_error` for a label between them — which is
    exactly what happened to `dispatch.NEIGHBOURHOOD_MAX`, and the whole suite stayed green
    through it.
    """
    connection = application.state.db
    load(client, accounts)
    triggers = {
        row["name"]: row["sql"] or ""
        for row in connection.execute(
            "select name, sql from sqlite_master where type = 'trigger'"
        )
    }

    # The haystack, before anything is said about the number in it.
    assert "decision_records_placement_shape" in triggers
    sql = triggers["decision_records_placement_shape"]
    bounds = [int(value) for value in re.findall(r"between 1 and (\d+)", sql)]
    assert bounds, f"no length bound in the trigger at all: {sql}"

    assert bounds == [decisions.CREW_LABEL_MAX] * len(bounds), (
        f"the store bounds a crew label at {bounds} and the service refuses at "
        f"{decisions.CREW_LABEL_MAX} — the endpoint's 400 becomes a 500 between them"
    )


def test_a_subject_that_disagrees_with_the_payload_is_refused(client, accounts, application):
    """`subject_id` is what makes a placement findable beside the recommendation for the same
    ranking, through the index migration 006 already created. A row whose subject says one
    revision and whose payload says another is a row that answers a different question depending
    on which half is read."""
    connection = application.state.db
    scenario_id = load(client, accounts)
    assets = ranked_assets(connection, scenario_id)

    disagreeing = refusal(
        connection,
        scenario_id,
        accounts["user"]["id"],
        payload(assets[:1]),
        subject_id=f"{scenario_id}:4",
    )
    not_a_ranking = refusal(
        connection,
        scenario_id,
        accounts["user"]["id"],
        payload(assets[:1]),
        subject_type="recommendation",
    )

    assert "recorded against the ranking" in disagreeing
    assert "recorded against the ranking" in not_a_ranking


def test_a_placement_with_no_forecast_revision_is_refused(client, accounts, application):
    """Half of *traceable to the ranking **and forecast revision*** — and the half a reader
    cannot reconstruct from anything else, because the pointer moves."""
    connection = application.state.db
    scenario_id = load(client, accounts)
    assets = ranked_assets(connection, scenario_id)
    body = json.loads(payload(assets[:1]))
    body.pop("forecast_revision")

    with pytest.raises(sqlite3.IntegrityError) as refused:
        insert(
            connection,
            scenario_id,
            accounts["user"]["id"],
            json.dumps(body),
            subject_id=f"{scenario_id}:0",
        )
    connection.rollback()

    assert "names the forecast revision" in str(refused.value)


def test_a_note_that_is_neither_absent_nor_text_is_refused(client, accounts, application):
    """The note is bounded in the store as well as in the request model, for the reason the
    crew label is: the request model is not what a direct insert passes through."""
    connection = application.state.db
    scenario_id = load(client, accounts)
    assets = ranked_assets(connection, scenario_id)

    over_long = refusal(
        connection, scenario_id, accounts["user"]["id"], payload(assets[:1], note="n" * 2001)
    )
    body = json.loads(payload(assets[:1]))
    body.pop("note")
    with pytest.raises(sqlite3.IntegrityError) as absent:
        insert(connection, scenario_id, accounts["user"]["id"], json.dumps(body))
    connection.rollback()

    assert "placement note" in over_long
    assert "placement note" in str(absent.value)


def test_an_actorless_placement_is_refused(client, accounts, application):
    """Migration 006's own rule, checked here because a placement is the first new `kind` written
    since it was made: *only the system's own recommendation may be actorless*. A crew placement
    nobody made is the audit trail's worst row."""
    connection = application.state.db
    scenario_id = load(client, accounts)
    assets = ranked_assets(connection, scenario_id)

    with pytest.raises(sqlite3.IntegrityError):
        insert(connection, scenario_id, None, payload(assets[:1]))
    connection.rollback()


def test_the_placement_rules_leave_every_other_kind_alone(client, accounts, application):
    """The trigger's `when` clause, asserted rather than assumed.

    A guard that fires on rows it was not written for is the same defect as one that does not
    fire at all, and it is quieter: this payload has no crew, no assets and no revision, and a
    row of another kind is entitled to lack all three.

    **The kind used here was `dismiss` until TASK-008, and it is `reject` now.** Nothing about
    this assertion changed — the placement trigger's `when` clause is still what is being
    checked — but CHG-035 gave `dismiss` a shape of its own, so a fabricated `dismiss` row is no
    longer a row *no* trigger has an opinion about, which is what this test needs. An ordinary
    human decision is: `decision_records_placement_shape` is the only guard that could fire on
    it, and it must not.
    """
    connection = application.state.db
    scenario_id = load(client, accounts)
    recommendation = connection.execute(
        "select id from decision_records where kind = 'recommendation'"
    ).fetchone()["id"]

    insert(
        connection,
        scenario_id,
        accounts["user"]["id"],
        json.dumps({"note": "Not this storm", "change": None}),
        kind="reject",
        subject_type="recommendation",
        subject_id=recommendation,
    )

    assert (
        connection.execute(
            "select kind from decision_records where id = 'DR-direct'"
        ).fetchone()["kind"]
        == "reject"
    )


def test_the_append_only_triggers_still_refuse_a_placement_row(client, accounts, application):
    """BR-004 reaches the new kind too. A placement is a decision record, and a correction is a
    new row — asserted against the database rather than against the absence of a code path."""
    connection = application.state.db
    scenario_id = load(client, accounts)
    assets = ranked_assets(connection, scenario_id)
    insert(connection, scenario_id, accounts["user"]["id"], payload(assets[:1]))

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("update decision_records set payload = '{}' where id = 'DR-direct'")
        connection.commit()
    connection.rollback()
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("delete from decision_records where id = 'DR-direct'")
        connection.commit()
    connection.rollback()

    assert connection.execute(
        "select count(*) from decision_records where id = 'DR-direct'"
    ).fetchone()[0] == 1


# CHG-039. Every one of these was answered `201` by `POST .../placements` on an untouched tree —
# no mutation needed — and two of them reached `decision_records`, which BR-004 forbids
# correcting. Each gets its own case for the reason the ASCII group above does: the clause you
# never ran is the clause whose function you assumed, and three languages mean three sets.
UNICODE_BLANKS = [
    " ",  # no-break space — Python strips it, JavaScript strips it, SQLite does not
    " ",  # em space
    "​",  # zero width space — NEITHER Python nor JavaScript strips it. This was a 201.
    "﻿",  # zero width no-break space — JavaScript strips it, Python does not. Also a 201.
    "　",  # ideographic space
    "",  # next line
    " ",  # line separator
    " ",  # narrow no-break space
]
BLANK_IDS = [f"U+{ord(character):04X}" for character in UNICODE_BLANKS]


@pytest.mark.parametrize("blank", UNICODE_BLANKS, ids=BLANK_IDS)
def test_the_store_refuses_a_crew_label_blank_in_any_alphabet(
    client, accounts, application, blank
):
    """**CHG-023's sentence for the fourth time, on the column TASK-007 created** (CHG-039).

    Migration 012 enumerated the same six ASCII characters CHG-037 had already had to widen one
    table over, and every character here got past them: SQLite's one-argument `trim()` strips
    spaces alone, and the five-way `replace` chain beside it named char(9) to char(13).
    """
    connection = application.state.db
    scenario_id = load(client, accounts)
    assets = ranked_assets(connection, scenario_id)

    message = refusal(
        connection, scenario_id, accounts["user"]["id"], payload(assets[:1], crew=blank)
    )

    assert "crew display label" in message


def test_an_ordinary_crew_label_still_goes_in(client, accounts, application):
    """The control the group above needs. Sixteen refusals prove nothing about *blankness* if
    the column is simply shut — this is the plain label, with an ordinary space in it, accepted
    by the same direct insert."""
    connection = application.state.db
    scenario_id = load(client, accounts)
    assets = ranked_assets(connection, scenario_id)

    insert(connection, scenario_id, accounts["user"]["id"], payload(assets[:1], crew="North crew"))

    stored = connection.execute(
        "select payload from decision_records where id = 'DR-direct'"
    ).fetchone()
    assert json.loads(stored["payload"])["crew"] == "North crew"


@pytest.mark.parametrize("blank", UNICODE_BLANKS, ids=BLANK_IDS)
def test_the_endpoint_refuses_a_crew_label_blank_in_any_alphabet(
    client, accounts, application, blank
):
    """The same hole from the caller's side, where it was live and needed no mutation at all.

    On an untouched tree `POST /api/v1/scenarios/{id}/placements` with a crew of U+200B or
    U+FEFF was answered **201**, and that single invisible character is what `decision_records`
    then held — a placement naming a crew nobody can see, under a person's name, in the one
    table a correction cannot reach. U+00A0, U+2003 and U+3000 were refused, so the failure was
    not even consistent: Python's `str.strip()` removes `White_Space` and neither invisible is
    in it.

    It was invisible from the screen because `PlacementForm` used `String.prototype.trim()`,
    which *does* remove U+FEFF — the strictest of the three definitions sitting in the layer
    ADR-002 says must never hold the rule.
    """
    connection = application.state.db
    scenario_id = load(client, accounts)
    assets = ranked_assets(connection, scenario_id)
    before = connection.execute(
        "select count(*) from decision_records where kind = 'placement'"
    ).fetchone()[0]

    refused = client.post(
        f"/api/v1/scenarios/{scenario_id}/placements",
        json={"crew": blank, "asset_ids": assets[:1], "forecast_revision": 0, "note": None},
    )

    assert refused.status_code == 400, refused.text
    assert refused.json()["code"] == "validation_error"
    assert "crew" in refused.json()["message"].lower()
    assert (
        connection.execute(
            "select count(*) from decision_records where kind = 'placement'"
        ).fetchone()[0]
        == before
    ), "a refused placement still wrote a row into the table BR-004 forbids correcting"


@pytest.mark.parametrize("blank", UNICODE_BLANKS, ids=BLANK_IDS)
def test_the_endpoint_keeps_a_crew_label_that_merely_contains_one(
    client, accounts, application, blank
):
    """The permitted case, and what stops the group above proving too much.

    A rule that refused every label containing an unusual character would satisfy all sixteen
    assertions above and would be wrong: CON-003 permits a display name, and a display name may
    be written in a language whose spaces are not U+0020. What is refused is a label made of
    nothing. The ends are trimmed with the shared alphabet and the rest is stored.
    """
    scenario_id = load(client, accounts)
    assets = ranked_assets(application.state.db, scenario_id)

    recorded = client.post(
        f"/api/v1/scenarios/{scenario_id}/placements",
        json={
            "crew": f"{blank}North crew{blank}",
            "asset_ids": assets[:1],
            "forecast_revision": 0,
            "note": None,
        },
    )

    assert recorded.status_code == 201, recorded.text
    stored = application.state.db.execute(
        "select payload from decision_records where kind = 'placement'"
        " order by occurred_at desc limit 1"
    ).fetchone()
    assert json.loads(stored["payload"])["crew"] == "North crew"


def test_one_alphabet_decides_what_is_blank_for_a_crew_label(client, accounts, application):
    """The tie, on the trigger this task owns (CHG-039).

    CHG-037 tied the schema, `store/dispatch.py` and the browser together for a dismissal
    reason and tied nothing to any other column, so the next column written reached for its own
    language's idea of blank. That is `AGENT.md`'s standing observation — a rule which has to be
    re-derived at each boundary will be missed at one — and this is what fails when a copy moves.
    """
    connection = application.state.db
    load(client, accounts)
    triggers = {
        row["name"]: row["sql"] or ""
        for row in connection.execute("select name, sql from sqlite_master where type = 'trigger'")
    }

    # The haystack, before anything is reported about what is in it.
    assert "decision_records_placement_shape" in triggers, "no placement trigger at all"
    sql = triggers["decision_records_placement_shape"]

    found = {
        tuple(int(point) for point in call.replace(" ", "").replace("\n", "").split(","))
        for call in re.findall(r"char\(([0-9,\s]+)\)", sql)
    }
    assert found, "the crew clause names no whitespace alphabet at all"

    full = tuple(blanks.BLANK_CODEPOINTS)
    without_the_space = tuple(point for point in full if point != 0x20)
    assert found == {full, without_the_space}, (
        "the crew label's alphabet and the store's disagree; the difference is which invisible "
        "characters a placement may be recorded under, in a table BR-004 forbids correcting"
    )
