"""TASK-009 done criteria 5, 6, 7, 8 and 9 — a loaded storm, as the store defines one.

**Every statement here is issued directly against the database.** `review-log.md` carries a
standing **Block** condition — *a rule enforced in the service layer that the store could
refuse* — and it has fired twice: once on a foreign key that proved existence and never
membership (CHG-019), and once on a `unique` constraint that could not see the normalisation
written in front of it (CHG-023). Both were found by asking **what can a direct insert put in
that column**, and that is the only question this file asks.

The rule under test is `data-and-integration-spec.md` §5: *"Loading a scenario whose content is
identical to one already loaded replaces that one in place; different content is a new scenario,
and several scenarios coexist."* Until this task that rule was `find_by_content_key` — a `select`
in front of an `insert`, in `api/scenarios.py` — and the digest it selected on was stored in
`scenarios.source_note`, the column `database-design.md` §3 defines as *which prepared dataset
this is, and where it came from*. So the switcher's third field was a hex string, the admin's
typed note was discarded, and two rows for one upload were something only the endpoint declined
to write (CHG-031).

**The positive case comes first in every group.** A store that refused every scenario would
satisfy every negative below and prove nothing — which is `AGENT.md`'s fourth lessons row, and
the reason four assertions in this repository turned out to be unfailable.

**Each refusal is read out of its message.** One trigger raises five different sentences and
they all arrive as `sqlite3.IntegrityError`; asserting the type would let any clause pass for
any other, which is the fifth lesson in the same table.
"""

import re
import sqlite3

import pytest
from app.store import blanks, scenarios
from conftest import USER_PASSWORD, build_application, fixture_files, sign_in
from fastapi.testclient import TestClient

# A well-formed content key: SHA-256, lower-case hex, 64 characters. Nothing about the digest's
# *value* is checked — only that the column can hold an identity at all.
KEY_A = "a" * 64
KEY_B = "b" * 64

# **Widened from the six ASCII characters to the shared alphabet** (CHG-039). It held
# `(" ", "\t", "\n", "\r", "\v", "\f")`, which is exactly the six the trigger and
# `store/scenarios.py` both enumerated — so the two layers agreed perfectly, were both wrong the
# same way, and this parametrisation could not tell. On an untouched tree
# `POST /api/v1/scenarios` with a name of one U+00A0 was answered **201** and stored, and
# `ScenarioSwitcher` — whose whole purpose under REQ-F-010 is letting a person pick one storm
# out of several — drew a row with no visible label. Reading the alphabet out of the store
# rather than restating it is the point: a seventh copy of this list is the defect again.
WHITESPACE = tuple(blanks.WHITESPACE)

AT_THE_NAME_LIMIT = "N" * scenarios.NAME_MAX
OVER_THE_NAME_LIMIT = "N" * (scenarios.NAME_MAX + 1)
AT_THE_NOTE_LIMIT = "S" * scenarios.SOURCE_NOTE_MAX
OVER_THE_NOTE_LIMIT = "S" * (scenarios.SOURCE_NOTE_MAX + 1)

INSERT = (
    "insert into scenarios"
    " (id, name, source_note, content_key, loaded_by, loaded_at, forecast_revision, seq)"
    " values (?, ?, ?, ?, ?, ?, 0, ?)"
)


def an_actor(connection) -> str:
    row = connection.execute("select id from users limit 1").fetchone()
    assert row is not None, "no user exists to own a scenario"
    return row["id"]


def insert(
    connection,
    *,
    row_id="SC-direct",
    name="Direct storm",
    source_note="written straight into the table",
    content_key=KEY_A,
    loaded_at="2026-08-16T00:00:00Z",
    seq=9001,
):
    """One scenario, written the way nothing in `backend/` writes one."""
    connection.execute(
        INSERT,
        (row_id, name, source_note, content_key, an_actor(connection), loaded_at, seq),
    )
    connection.commit()


def refusal(connection, **kwargs) -> str:
    with pytest.raises(sqlite3.IntegrityError) as refused:
        insert(connection, **kwargs)
    connection.rollback()
    return str(refused.value)


@pytest.fixture
def signed_in(client, accounts):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    return client


def load(client, *, name="Helene replay", source_note="NOAA 2024 replay pack", fixture=None):
    files = fixture_files(fixture) if fixture else fixture_files()
    return client.post(
        "/api/v1/scenarios",
        data={"name": name, "source_note": source_note},
        files=[("files", (n, c, "text/csv")) for n, c in files.items()],
    )


# --------------------------------------------------------------------------------------------
# Criterion 5 — one upload is one storm, and the store is what says so.
# --------------------------------------------------------------------------------------------


def test_a_well_formed_scenario_is_accepted_by_a_direct_insert(client, accounts, application):
    """The haystack. Everything below is *this row, with one thing wrong*."""
    connection = application.state.db

    insert(connection)

    stored = connection.execute(
        "select name, source_note, content_key from scenarios where id = 'SC-direct'"
    ).fetchone()
    assert stored["name"] == "Direct storm"
    assert stored["source_note"] == "written straight into the table"
    assert stored["content_key"] == KEY_A


def test_a_second_row_for_the_same_upload_is_refused(client, accounts, application):
    """§5, as something the database will not accept.

    Two rows for one prepared storm is the switcher asking a person to choose between a thing
    and itself, and each copy carries its own ranking for the same weather — so a decision
    recorded against one of them is a decision about a list the other reader never saw.
    """
    connection = application.state.db
    insert(connection, row_id="SC-first")

    refused = refusal(connection, row_id="SC-second", name="A rival copy")

    assert "content_key" in refused or "unique" in refused.lower()
    assert connection.execute("select count(*) from scenarios").fetchone()[0] == 1


def test_a_different_upload_is_a_different_storm(client, accounts, application):
    """The other half of §5: *different content is a new scenario, and several coexist.* A store
    that refused the second insert for any reason would pass the test above."""
    connection = application.state.db
    insert(connection, row_id="SC-first", content_key=KEY_A)

    insert(connection, row_id="SC-second", content_key=KEY_B, seq=9002)

    assert connection.execute("select count(*) from scenarios").fetchone()[0] == 2


def test_the_endpoint_refuses_a_rival_copy_the_same_way(signed_in, application):
    """And through the door a person uses. The 200-with-the-existing-id path is `§5`'s
    *replaces in place*; what matters here is that it is the store that makes it true."""
    first = load(signed_in)
    assert first.status_code == 201, first.text

    again = load(signed_in, name="A rival copy", source_note="a completely different note")

    assert again.status_code == 200, again.text
    assert again.json()["scenario_id"] == first.json()["scenario_id"]
    connection = application.state.db
    assert connection.execute("select count(*) from scenarios").fetchone()[0] == 1


# --------------------------------------------------------------------------------------------
# Criterion 6 — a storm the store cannot identify, or a screen cannot show, is not written.
# One case per clause, and each names its own clause.
# --------------------------------------------------------------------------------------------


def test_a_scenario_with_no_content_key_is_refused(client, accounts, application):
    """The hole a nullable column would leave. `unique` permits any number of nulls in SQLite,
    so without this clause two storms with no identity at all coexist happily — and §5's rule
    would hold for every row except the ones written around the endpoint."""
    refused = refusal(application.state.db, content_key=None)

    assert "content" in refused


@pytest.mark.parametrize(
    "key",
    [
        "a" * 63,
        "a" * 65,
        "A" * 64,  # upper case: `hexdigest()` never produces it, so it is a second spelling
        "g" * 64,  # not hexadecimal at all
        "a" * 32 + " " * 32,
        "",
    ],
    ids=["short", "long", "upper-case", "not-hex", "padded", "empty"],
)
def test_a_content_key_that_is_not_a_digest_is_refused(client, accounts, application, key):
    """CHG-023's lesson, applied to the column identity now rests on: *an unexercised clause is
    a claim nobody has ever read back.* A key of the wrong length, the wrong alphabet or the
    wrong case is a second spelling of one storm, and `unique` cannot see past a spelling."""
    refused = refusal(application.state.db, content_key=key)

    assert "content" in refused


def test_a_blank_source_note_is_refused(client, accounts, application):
    """§3: `source_note: string, **required**` — *which prepared dataset this is, and where it
    came from*. An empty one is a switcher row that says where a storm came from and does not."""
    refused = refusal(application.state.db, source_note="")

    assert "source" in refused


@pytest.mark.parametrize("blank", WHITESPACE, ids=[repr(c) for c in WHITESPACE])
def test_a_whitespace_only_source_note_is_refused(client, accounts, application, blank):
    """Every whitespace character, enumerated, because SQLite's one-argument `trim()` strips
    **spaces only** — a fact this repository learned by writing the missing cases for
    `damage_reports.location` and finding that `'   '` was refused while a tab-and-newline was
    stored (CHG-023). The same clause written the same way would have the same hole."""
    refused = refusal(application.state.db, source_note=blank * 4)

    assert "source" in refused


def test_a_source_note_at_the_bound_is_accepted_and_one_over_it_is_refused(
    client, accounts, application
):
    connection = application.state.db

    insert(connection, row_id="SC-at", source_note=AT_THE_NOTE_LIMIT)

    assert connection.execute(
        "select length(source_note) from scenarios where id = 'SC-at'"
    ).fetchone()[0] == scenarios.SOURCE_NOTE_MAX
    assert "source" in refusal(
        connection, row_id="SC-over", content_key=KEY_B, source_note=OVER_THE_NOTE_LIMIT
    )


def test_a_blank_name_is_refused(client, accounts, application):
    refused = refusal(application.state.db, name="")

    assert "name" in refused


@pytest.mark.parametrize("blank", WHITESPACE, ids=[repr(c) for c in WHITESPACE])
def test_a_whitespace_only_name_is_refused(client, accounts, application, blank):
    refused = refusal(application.state.db, name=blank * 4)

    assert "name" in refused


def test_a_name_at_the_bound_is_accepted_and_one_over_it_is_refused(
    client, accounts, application
):
    connection = application.state.db

    insert(connection, row_id="SC-at", name=AT_THE_NAME_LIMIT)

    assert connection.execute(
        "select length(name) from scenarios where id = 'SC-at'"
    ).fetchone()[0] == scenarios.NAME_MAX
    assert "name" in refusal(
        connection, row_id="SC-over", content_key=KEY_B, name=OVER_THE_NAME_LIMIT
    )


def test_the_identity_of_a_loaded_storm_cannot_be_rewritten(client, accounts, application):
    """The insert guard says what may be written; without this one an `UPDATE` walks around all
    of it — a storm renamed to blank, or given another storm's digest, is the same defect
    arriving through a different statement."""
    connection = application.state.db
    insert(connection)

    for column, value in (
        ("content_key", KEY_B),
        ("name", "Renamed"),
        ("source_note", "somewhere else entirely"),
    ):
        with pytest.raises(sqlite3.IntegrityError) as refused:
            connection.execute(
                f"update scenarios set {column} = ? where id = 'SC-direct'", (value,)
            )
            connection.commit()
        connection.rollback()
        assert "identity" in str(refused.value)

    # The haystack: the pointer this table exists to move is still movable.
    connection.execute("update scenarios set forecast_revision = 0 where id = 'SC-direct'")
    connection.commit()


def test_the_scenario_rules_leave_every_other_table_alone(client, accounts, application):
    """A trigger conditioned on the wrong table, or renamed, does not stop being a trigger —
    which is how a mutation that "removed" a guard reported a clean bill twice in this
    repository. A row in a neighbouring table with a blank text column is still accepted."""
    connection = application.state.db
    insert(connection)

    connection.execute(
        "insert into scenario_uploads"
        " (id, status, uploaded_by, uploaded_at, name, source_note, storage_path)"
        " values ('UP-blank', 'parsing', ?, '2026-08-16T00:00:00Z', '', '', '/tmp/x')",
        (an_actor(connection),),
    )
    connection.commit()

    assert connection.execute(
        "select count(*) from scenario_uploads where id = 'UP-blank'"
    ).fetchone()[0] == 1


# --------------------------------------------------------------------------------------------
# Criterion 7 — one bound governs each column.
# --------------------------------------------------------------------------------------------


def test_one_bound_governs_the_name_and_one_governs_the_source_note(
    client, accounts, application
):
    """CHG-023's other half, applied before it bites rather than after.

    Two hard-coded copies of one number are tied together by nothing, and when they drift the
    endpoint's specified `400 validation_error` becomes a `500 internal_error` for a value
    between them — which is exactly what happened to `dispatch.NEIGHBOURHOOD_MAX`, with the
    whole suite green through it.
    """
    connection = application.state.db
    triggers = {
        row["name"]: row["sql"] or ""
        for row in connection.execute("select name, sql from sqlite_master where type = 'trigger'")
    }

    # The haystack, before anything is said about the numbers in it.
    assert "scenarios_identity_shape" in triggers
    sql = triggers["scenarios_identity_shape"]
    bounds = [int(value) for value in re.findall(r"between 1 and (\d+)", sql)]
    assert len(bounds) == 2, f"expected exactly two length bounds in the trigger, found {bounds}"

    assert bounds == [scenarios.NAME_MAX, scenarios.SOURCE_NOTE_MAX], (
        f"the store bounds a storm's name and note at {bounds} and the service refuses at "
        f"{[scenarios.NAME_MAX, scenarios.SOURCE_NOTE_MAX]} — the endpoint's 400 becomes a 500 "
        "between them"
    )


def test_the_endpoint_refuses_an_over_long_name_with_the_status_the_contract_names(signed_in):
    """The other end of the same tie: a `500` here means the trigger fired where the request
    model should have."""
    refused = load(signed_in, name=OVER_THE_NAME_LIMIT)

    assert refused.status_code == 400, refused.text
    assert "name" in refused.json()["message"]


def test_the_endpoint_refuses_a_blank_source_note_with_the_status_the_contract_names(signed_in):
    refused = load(signed_in, source_note="   ")

    assert refused.status_code == 400, refused.text
    assert "source note" in refused.json()["message"]


# --------------------------------------------------------------------------------------------
# Criterion 8 — the list has a total order, and a clock is not one.
# --------------------------------------------------------------------------------------------


def test_two_storms_loaded_in_one_tick_keep_the_order_they_were_loaded(
    signed_in, application, monkeypatch
):
    """CHG-018's decision, on the fourth table read as a list.

    `datetime.now(UTC).isoformat()` resolves to about **15.6 ms** on this platform — 1,999 of
    2,000 consecutive calls return an identical string — and `scenarios.id` is a random UUID, so
    `order by loaded_at desc, id` is a coin flip for two storms loaded in one tick. The clock is
    pinned here rather than hoped about: **the three storms below have byte-identical
    `loaded_at` values**, so a list ordered by time cannot tell them apart at all and only a
    sequence can.
    """
    monkeypatch.setattr(scenarios, "_now", lambda: "2026-08-16T09:00:00.000000+00:00")
    first = load(signed_in, name="First in", fixture="storm-with-seven-defects")
    second = load(signed_in, name="Second in", fixture="storm-with-a-forecast-change")
    third = load(signed_in, name="Third in", fixture="storm-for-the-planning-flow")
    assert [r.status_code for r in (first, second, third)] == [201, 201, 201]
    loaded = [r.json()["scenario_id"] for r in (first, second, third)]

    connection = application.state.db
    stamps = [
        row["loaded_at"] for row in connection.execute("select loaded_at from scenarios")
    ]
    # The premise: the clock genuinely cannot separate them.
    assert len(set(stamps)) == 1, f"the three storms have different timestamps: {stamps}"
    sequences = {
        row["id"]: row["seq"] for row in connection.execute("select id, seq from scenarios")
    }
    assert len(set(sequences.values())) == 3, "two storms claim one place in the order"
    assert [sequences[i] for i in loaded] == sorted(sequences[i] for i in loaded)

    listed = signed_in.get("/api/v1/scenarios").json()
    assert [item["scenario_id"] for item in listed["items"]] == list(reversed(loaded))
    assert [item["name"] for item in listed["items"]] == ["Third in", "Second in", "First in"]


def test_two_storms_cannot_claim_one_place_in_the_order(client, accounts, application):
    """`unique (seq)`, asserted directly. A sequence the store does not enforce is a counter,
    and a counter held anywhere but in the table comes back as 1 after a restart."""
    connection = application.state.db
    insert(connection, row_id="SC-first", seq=7)

    refused = refusal(connection, row_id="SC-second", content_key=KEY_B, seq=7)

    assert "seq" in refused or "unique" in refused.lower()


# --------------------------------------------------------------------------------------------
# Criterion 9 — the list is durable state, and a task that introduces durable state owns its
# restart test (`AGENT.md`, second lessons row, and the paragraph beneath it).
# --------------------------------------------------------------------------------------------


def test_the_list_its_notes_and_its_order_survive_a_restart(tmp_path, monkeypatch):
    """The mutation this exists for: hold the sequence beside the connection —
    `_SEQ[id(connection)] += 1` — instead of taking it from the table inside the insert. Within
    one process it is indistinguishable. Over a restart the counter goes back to 1, `unique
    (seq)` refuses the next storm, and the first thing an admin loads after the service comes
    back is a `500`.

    **The values are asserted, not the arrangement.** TASK-006's restart test compared two
    stored orders and said nothing about the numbers behind them, and a whole storm re-ranked to
    nothing passed it.
    """
    from app.store import users

    database = tmp_path / "storms.db"

    before = build_application(monkeypatch, database)
    users.create_user(
        before.state.db,
        name="Ops Manager",
        email="admin@sgw.example",
        password=USER_PASSWORD,
        role="admin",
    )
    first_client = TestClient(before)
    assert sign_in(first_client, "admin@sgw.example", USER_PASSWORD).status_code == 201
    assert load(
        first_client, name="First in", source_note="NOAA replay pack",
        fixture="storm-with-seven-defects",
    ).status_code == 201
    assert load(
        first_client, name="Second in", source_note="Forecast-change rehearsal",
        fixture="storm-with-a-forecast-change",
    ).status_code == 201
    was = first_client.get("/api/v1/scenarios").json()
    assert [item["name"] for item in was["items"]] == ["Second in", "First in"]
    before.state.db.close()  # the restart

    after = build_application(monkeypatch, database)
    second_client = TestClient(after)
    assert sign_in(second_client, "admin@sgw.example", USER_PASSWORD).status_code == 201

    now = second_client.get("/api/v1/scenarios").json()
    assert [item["scenario_id"] for item in now["items"]] == [
        item["scenario_id"] for item in was["items"]
    ]
    assert [item["name"] for item in now["items"]] == ["Second in", "First in"]
    assert [item["source_note"] for item in now["items"]] == [
        "Forecast-change rehearsal",
        "NOAA replay pack",
    ]

    # And a third storm can still be loaded, which is the half a counter in process memory
    # fails: it would restart at 1 and collide with the sequence already in the table.
    assert load(
        second_client, name="Third in", source_note="Planning rehearsal",
        fixture="storm-for-the-planning-flow",
    ).status_code == 201
    assert [item["name"] for item in second_client.get("/api/v1/scenarios").json()["items"]] == [
        "Third in",
        "Second in",
        "First in",
    ]


# --------------------------------------------------------------------------------------------
# CHG-039 — the alphabet reaches this table too, and both halves were live without a mutation.
# --------------------------------------------------------------------------------------------

# The characters the six-ASCII list above could not see. Two of them are the ones no language
# strips for you: U+200B is in neither Python's `White_Space` nor JavaScript's `trim()`, and
# U+FEFF is in JavaScript's and not in Python's.
INVISIBLES = [
    " ",  # no-break space — this one was a live 201 and a stored storm name
    " ",  # em space
    "​",  # zero width space
    "﻿",  # zero width no-break space
    "　",  # ideographic space
]
INVISIBLE_IDS = [f"U+{ord(character):04X}" for character in INVISIBLES]


@pytest.mark.parametrize("blank", INVISIBLES, ids=INVISIBLE_IDS)
def test_the_endpoint_refuses_a_storm_named_in_no_visible_character(signed_in, application, blank):
    """**Live on an untouched tree, with no mutation at all** (CHG-039).

    `POST /api/v1/scenarios` with `name` set to one no-break space was answered **201** and that
    character is what `scenarios.name` then held. REQ-F-010 is about choosing between several
    loaded storms and `ScenarioSwitcher` is the screen that does it, so a storm whose label is
    invisible is a row a person cannot pick and cannot tell apart from the one beside it.

    `'   '` was refused the whole time, which is what made it invisible as a defect as well:
    the rule looked present and was six characters wide. `ScenarioUploadPanel` used
    `String.prototype.trim()`, which removes this character — the browser strictest again, so
    only a caller reaching the API ever met it.
    """
    before = application.state.db.execute("select count(*) from scenarios").fetchone()[0]

    refused = load(signed_in, name=blank)

    assert refused.status_code == 400, refused.text
    assert refused.json()["code"] == "validation_error"
    assert "name" in refused.json()["message"].lower()
    assert application.state.db.execute("select count(*) from scenarios").fetchone()[0] == before


@pytest.mark.parametrize("blank", INVISIBLES, ids=INVISIBLE_IDS)
def test_the_endpoint_refuses_a_source_note_of_no_visible_character(
    signed_in, application, blank
):
    """§3's *which prepared dataset this is, and where it came from*, held to the same alphabet.

    The note is what the switcher shows beneath the name, so an invisible one is a row that
    claims to say where a storm came from and says nothing — and `api/scenarios.py` cannot fall
    back to `UNSTATED_SOURCE`, because the caller did supply a value.
    """
    before = application.state.db.execute("select count(*) from scenarios").fetchone()[0]

    refused = load(signed_in, source_note=blank)

    assert refused.status_code == 400, refused.text
    assert refused.json()["code"] == "validation_error"
    assert "source" in refused.json()["message"].lower()
    assert application.state.db.execute("select count(*) from scenarios").fetchone()[0] == before


@pytest.mark.parametrize("blank", INVISIBLES, ids=INVISIBLE_IDS)
def test_a_storm_whose_name_merely_contains_one_is_loaded_and_trimmed(
    signed_in, application, blank
):
    """The permitted case, and what stops the two groups above proving too much.

    A rule that refused every name containing an unusual space would be wrong — a storm named in
    Japanese uses U+3000 between its words. What is refused is a name made of nothing. The ends
    are trimmed with the shared alphabet and what a person typed in the middle is theirs.
    """
    created = load(signed_in, name=f"{blank}Helene replay{blank}")

    assert created.status_code == 201, created.text
    stored = application.state.db.execute(
        "select name from scenarios where id = ?", (created.json()["scenario_id"],)
    ).fetchone()
    assert stored["name"] == "Helene replay"


def test_one_alphabet_decides_what_is_blank_for_a_storms_label(client, accounts, application):
    """The tie, on the trigger this task owns (CHG-039).

    CHG-037 tied three copies of the alphabet together for a dismissal reason and tied nothing
    to any other column, so this table's two text columns went on being trimmed by the six ASCII
    characters in `store/scenarios.py` and the identical six in `scenarios_identity_shape`. The
    two agreed with each other perfectly, which is why nothing was ever red. Move any copy now
    and this is.
    """
    connection = application.state.db
    triggers = {
        row["name"]: row["sql"] or ""
        for row in connection.execute("select name, sql from sqlite_master where type = 'trigger'")
    }

    # The haystack, before anything is reported about what is in it.
    assert "scenarios_identity_shape" in triggers, "no identity trigger at all"
    sql = triggers["scenarios_identity_shape"]

    found = {
        tuple(int(point) for point in call.replace(" ", "").replace("\n", "").split(","))
        for call in re.findall(r"char\(([0-9,\s]+)\)", sql)
    }
    assert found, "the name and source-note clauses name no whitespace alphabet at all"
    assert found == {tuple(blanks.BLANK_CODEPOINTS)}, (
        "the schema and `store/blanks.py` disagree about what is blank; the difference is "
        "whether a storm can be loaded under a name nobody can see on the switcher"
    )
    assert tuple(scenarios._WHITESPACE) == tuple(blanks.WHITESPACE), (
        "the service layer trims a different alphabet from the one the store refuses, which "
        "turns the specified 400 into a 500 for every character between them"
    )
