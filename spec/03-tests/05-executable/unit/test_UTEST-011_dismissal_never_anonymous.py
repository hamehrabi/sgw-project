"""UTEST-011 — REQ-F-008. Defined in `03-tests/02-functional/unit-tests.md`.

Rule under test: **a dismissal is one action but never anonymous.**
  normal  — dismissal with actor and reason succeeds
  edge    — a one-character reason is accepted; brevity is not the rule
  failure — a dismissal with no actor or no reason → **refused by the store**

`edge-cases-and-failures.md` names the risk in one line: *an anonymous dismissal — control made
cheap and untraceable.* That is the whole tension in REQ-F-008. Making the action cheap is the
requirement; the price of cheap is that it stops carrying a name, and a report vanishing from a
shared board with nobody's name on it is worse than a report nobody cleared.

**Every refusal below is issued directly against the database**, not through the endpoint
(ADR-002, and `executable-tests.md`'s note that three tests sit below the application and must
stay there). The endpoint is the thing being tested; it is not the guarantee.

**Every refusal is paired with an acceptance that differs in exactly one field.** The store's
message for a table check is `CHECK constraint failed: <name>`, so the constraint is *named* in
migration 014 and the tests read the name out of the refusal — but a name is not enough on its
own: it says which constraint fired, not which clause of it. The paired control is what says the
clause. That is the lessons row about a clause no test ever violates, applied while writing
rather than after a review finds it.
"""

import json
import logging
import pathlib
import re
import sqlite3

import pytest
from app.store import decisions, dispatch
from conftest import USER_PASSWORD, build_application, sign_in
from fastapi.testclient import TestClient

ATTRIBUTED = "CHECK constraint failed: damage_reports_dismissal_is_attributed"
NEVER_REWRITTEN = "never rewritten"
# The two clauses of `decision_records_dismiss_shape`, named separately on purpose: a status
# code is a category and so is an exception class, so every refusal below reads the sentence
# that identifies **which** rule refused it.
SUBJECT_IS_A_REPORT = "names a damage report as its subject"
AGREES_WITH_THE_REPORT = "must agree with the report it names"
# CHG-036's refusal, read the same way. SQLite does not let an index carry a sentence, and this
# message identifies the rule and no other: `decision_records (subject_id) where kind =
# 'dismiss'` is the only unique constraint on that column, and the only one on the table beside
# its primary key. Escaped because `pytest.raises(match=...)` is a regular expression.
ONE_AUDIT_ROW = r"UNIQUE constraint failed: decision_records\.subject_id"
A_REASON = "Tree was already cleared - no damage to the line"

# The frontend's copies of the bound and the alphabet. Read as source rather than mirrored a
# fourth time here — the point of the two tests at the bottom of this file is that a rule with
# several homes needs something that fails when the copies disagree (CHG-037).
FRONTEND = pathlib.Path(__file__).resolve().parents[4] / "frontend"


def a_storm(application, accounts, scenario_id="SC-dismissal", seq=800, content_key="e" * 64):
    """A scenario row and nothing else. This rule needs no assets to be broken.

    `seq` and `content_key` are parameters because two of the cases below need a **second**
    storm, and both columns are `unique` (CHG-031, CHG-032) — a storm has an identity and a
    place in the order storms are listed in, and a direct insert has to satisfy the store like
    any other writer.
    """
    application.state.db.execute(
        "insert into scenarios (id, name, source_note, content_key, loaded_by, loaded_at,"
        " forecast_revision, seq)"
        " values (?, 'Dismissal storm', 'unit', ?, ?, '2026-08-16T00:00:00Z', 0, ?)",
        (scenario_id, content_key, accounts["admin"]["id"], seq),
    )
    application.state.db.commit()
    return scenario_id


def file_report(client, scenario_id, neighbourhood="Northgate") -> str:
    response = client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports", json={"neighbourhood": neighbourhood}
    )
    assert response.status_code == 201, response.text
    return response.json()["report_id"]


def file_report_naming(client, scenario_id, neighbourhood, asset_id) -> str:
    """A report that may name an asset, so the per-asset figure can be a different number from
    the neighbourhood's."""
    response = client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports",
        json={"neighbourhood": neighbourhood, "asset_id": asset_id},
    )
    assert response.status_code == 201, response.text
    return response.json()["report_id"]


def a_filed_report(client, application, accounts, neighbourhood="Northgate"):
    """Signed in as the dispatcher, one storm, one open report."""
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    scenario_id = a_storm(application, accounts)
    return scenario_id, file_report(client, scenario_id, neighbourhood)


def an_unattached_report(
    application, scenario_id, neighbourhood="Fen Causeway", report_id="DR-no-job", seq=9500
):
    """A report belonging to **no repair job** — CHG-022's state, and the one this task never
    dismissed.

    `repair_job_id` is optional in `database-design.md` §3 and §1 says a report belongs *"to at
    most one repair job"*, so the state exists and `DispatchBoard` renders a `DismissAlarmControl`
    on every one of them. There is no endpoint that produces it — the filing endpoint always
    finds or creates a job — so it is written the way UTEST-012 writes it, directly.
    """
    application.state.db.execute(
        "insert into damage_reports"
        " (id, scenario_id, location, reported_at, reported_by, status, seq)"
        " values (?, ?, ?, '2026-08-16T00:00:00Z', 'radio-2', 'open', ?)",
        (report_id, scenario_id, json.dumps({"neighbourhood": neighbourhood}), seq),
    )
    application.state.db.commit()
    return report_id


def dismiss_directly(connection, report_id, *, actor, reason):
    """The dismissal as a statement, with no application anywhere near it."""
    connection.execute(
        "update damage_reports set status = 'dismissed', dismissed_by = ?, dismissed_reason = ?"
        " where id = ?",
        (actor, reason, report_id),
    )


def stored(connection, report_id) -> sqlite3.Row:
    return connection.execute(
        "select * from damage_reports where id = ?", (report_id,)
    ).fetchone()


def everything_logged(caplog):
    parts = []
    for record in caplog.records:
        parts.append(record.getMessage())
        parts.extend(
            f"{key}={value}"
            for key, value in record.__dict__.items()
            if key not in logging.LogRecord("", 0, "", 0, "", (), None).__dict__
        )
    return "\n".join(parts)


# ---------------------------------------------------------------------------------------------
# The failure case: refused by the store
# ---------------------------------------------------------------------------------------------


def test_the_store_refuses_a_dismissal_with_no_actor(client, application, accounts):
    """*Who dismissed it* — half of REQ-F-008, and the half `database-design.md` §3 already
    carried. Asserted against the database, with the identical row **plus an actor** accepted
    beside it, so this cannot be passing because the store refuses the update in general."""
    _, report_id = a_filed_report(client, application, accounts)
    connection = application.state.db

    with pytest.raises(sqlite3.IntegrityError, match=ATTRIBUTED):
        dismiss_directly(connection, report_id, actor=None, reason=A_REASON)
    connection.rollback()

    dismiss_directly(connection, report_id, actor=accounts["user"]["id"], reason=A_REASON)
    connection.commit()
    assert stored(connection, report_id)["status"] == "dismissed"


@pytest.mark.parametrize(
    "reason",
    [
        None,
        # CHG-033. Every one of these satisfied `dismissed_reason is not null` and is not a
        # reason. `'\t\n'` is the case CHG-023 found on the column beside this one: SQLite's
        # one-argument `trim()` strips **spaces only**, so the same non-answer was refused when
        # spelled with spaces and stored when spelled with a tab.
        "",
        "   ",
        "\t\n",
        " \r\v\f ",
        # Stored untrimmed is a second spelling of one reason, and this repository has already
        # paid twice for a column that holds two spellings of one fact (CHG-023, CHG-031).
        "  padded  ",
    ],
)
def test_the_store_refuses_a_dismissal_with_no_reason(client, application, accounts, reason):
    """*And why* — the other half, and the half nothing enforced. Each case differs from the
    accepted control below in the reason alone."""
    _, report_id = a_filed_report(client, application, accounts)
    connection = application.state.db

    with pytest.raises(sqlite3.IntegrityError, match=ATTRIBUTED):
        dismiss_directly(connection, report_id, actor=accounts["user"]["id"], reason=reason)
    connection.rollback()

    assert stored(connection, report_id)["status"] == "open"


def test_the_store_refuses_a_reason_longer_than_the_bound(client, application, accounts):
    """The upper bound, from the refused side. One character over, with the permitted length
    asserted in the next test, so this is refusing a length rather than refusing long text."""
    _, report_id = a_filed_report(client, application, accounts)
    connection = application.state.db

    with pytest.raises(sqlite3.IntegrityError, match=ATTRIBUTED):
        dismiss_directly(
            connection,
            report_id,
            actor=accounts["user"]["id"],
            reason="N" * (dispatch.DISMISSAL_REASON_MAX + 1),
        )
    connection.rollback()


@pytest.mark.parametrize(
    "reason",
    [
        A_REASON,
        # The edge case `unit-tests.md` names: *a one-character reason is accepted — brevity is
        # not the rule*. What the rule refuses is absence, not shortness, and a dispatcher
        # typing `x` during a storm has still put their name to it.
        "x",
        "N" * dispatch.DISMISSAL_REASON_MAX,
        # Prose. A reason is somebody's sentence, so an internal newline is not a defect —
        # only a leading or trailing one is, and only a reason made of nothing else.
        "Two calls, one pole.\nThe second was the same pole.",
    ],
)
def test_the_store_accepts_a_dismissal_that_carries_an_actor_and_a_reason(
    client, application, accounts, reason
):
    """The normal case and the edge case, against the store. Without these the refusals above
    are satisfied by a constraint that refuses every dismissal."""
    _, report_id = a_filed_report(client, application, accounts)
    connection = application.state.db

    dismiss_directly(connection, report_id, actor=accounts["user"]["id"], reason=reason)
    connection.commit()

    row = stored(connection, report_id)
    assert (row["status"], row["dismissed_by"], row["dismissed_reason"]) == (
        "dismissed",
        accounts["user"]["id"],
        reason,
    )


def test_a_report_that_is_not_dismissed_needs_neither(client, application, accounts):
    """**The silent case for the whole constraint.** It governs dismissals; an open report and a
    duplicate one carry no actor and no reason and must still be storable. A check written
    without the `status <> 'dismissed' or` guard would pass every test above and make filing an
    ordinary damage report impossible."""
    scenario_id, report_id = a_filed_report(client, application, accounts)
    connection = application.state.db
    assert stored(connection, report_id)["dismissed_reason"] is None

    connection.execute(
        "update damage_reports set status = 'duplicate' where id = ?", (report_id,)
    )
    connection.commit()

    row = stored(connection, report_id)
    assert (row["status"], row["dismissed_by"], row["dismissed_reason"]) == (
        "duplicate",
        None,
        None,
    )


# The characters that made `'   '` a refusal and one of these a stored reason (CHG-037). Not the
# whole alphabet — the whole alphabet is asserted by
# `test_one_alphabet_decides_what_is_blank_in_every_layer`; these are the ones a caller actually
# reaches for, and the four the review found answered `201` on an untouched tree.
UNICODE_BLANKS = [
    " ",  # no-break space
    " ",  # em space
    "​",  # zero width space
    "﻿",  # zero width no-break space
    "　",  # ideographic space
    "",  # next line
    " ",  # line separator
    " ",  # narrow no-break space
]
BLANK_IDS = [f"U+{ord(character):04X}" for character in UNICODE_BLANKS]


@pytest.mark.parametrize("blank", UNICODE_BLANKS, ids=BLANK_IDS)
def test_the_store_refuses_a_reason_that_is_blank_in_any_alphabet(
    client, application, accounts, blank
):
    """**CHG-023's sentence for the third time, on the column CHG-033 was written to close.**

    Migration 014 enumerated six ASCII characters and every one of these got past them. The
    accepted control puts the *same* character **inside** the reason: what the rule refuses is a
    reason made of nothing, never a character — a dispatcher writing a Japanese neighbourhood's
    name into a sentence has still put their name to it.
    """
    _, report_id = a_filed_report(client, application, accounts)
    connection = application.state.db

    with pytest.raises(sqlite3.IntegrityError, match=ATTRIBUTED):
        dismiss_directly(connection, report_id, actor=accounts["user"]["id"], reason=blank)
    connection.rollback()
    assert stored(connection, report_id)["status"] == "open"

    inside = f"x{blank}y"
    dismiss_directly(connection, report_id, actor=accounts["user"]["id"], reason=inside)
    connection.commit()
    assert stored(connection, report_id)["dismissed_reason"] == inside


@pytest.mark.parametrize("blank", UNICODE_BLANKS, ids=BLANK_IDS)
def test_the_endpoint_refuses_a_reason_that_is_blank_in_any_alphabet(
    client, application, accounts, blank
):
    """The same hole from the caller's side, where it was live and needed no mutation at all.

    On the untouched tree this request was answered **201** and that single invisible character
    was what `dismissed_reason` and the audit row held, under the dispatcher's name. It was
    invisible on screen because the browser's `String.prototype.trim()` was the **strictest** of
    the three definitions — the enforcement had ended up in the one layer ADR-002 says it must
    never live in, so only a caller reaching the API ever met it.
    """
    _, report_id = a_filed_report(client, application, accounts)

    refused = client.post(f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": blank})

    assert refused.status_code == 400, refused.text
    assert refused.json()["code"] == "validation_error"
    row = stored(application.state.db, report_id)
    assert (row["status"], row["dismissed_by"], row["dismissed_reason"]) == ("open", None, None)

    # And the same character at the ends of a real reason is trimmed rather than refused, so the
    # `400` above is about a reason made of nothing and not about the character.
    accepted = client.post(
        f"/api/v1/damage-reports/{report_id}/dismiss",
        json={"reason": f"{blank}Wrong street{blank}"},
    )
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["dismissed_reason"] == "Wrong street"


CHAR_CALL = re.compile(r"char\(([0-9,\s]+)\)")
# Widened from `DISMISSAL_BLANK_CODEPOINTS` to the suffix alone (CHG-039). The alphabet was
# never a fact about dismissals — two other fields kept `String.prototype.trim()` because the
# shared definition was filed under a name that did not look like theirs — and it now lives in
# `lib/blank.ts` as `BLANK_CODEPOINTS`. **This is a wider haystack, not a narrower assertion:**
# the pattern still matches the old spelling, so a file that re-introduces one is still counted,
# and `len(listed) == 1` below is still what refuses a second home.
BLANK_LIST = re.compile(r"BLANK_CODEPOINTS\s*=\s*\[(.*?)\]", re.DOTALL)
FRONTEND_BOUND = re.compile(r"DISMISSAL_REASON_MAX\s*=\s*(\d+)")


def frontend_sources() -> dict[pathlib.Path, str]:
    """Every TypeScript file the browser half is built from.

    Enumerated rather than named one by one so a fourth copy of either rule cannot appear in a
    file this test does not know about — which is exactly how the bound acquired its third and
    fourth copies.
    """
    return {
        path: path.read_text(encoding="utf-8")
        for directory in ("lib", "views", "app", "e2e")
        for path in sorted((FRONTEND / directory).rglob("*.ts*"))
    }


def test_one_alphabet_decides_what_is_blank_in_every_layer(application):
    """**The rule had three homes and the three disagreed** (CHG-037).

    The schema enumerated six ASCII characters, `dispatch.WHITESPACE` repeated the same six, and
    the browser used `String.prototype.trim()`, which is Unicode-aware. Nothing failed when they
    disagreed, so nothing did — and a reason of one no-break space was a `201`.

    This is the tie: move any one of the three and it is red. It is `AGENT.md`'s row about a
    bound written in more than one place, applied to an alphabet, which is the same kind of
    thing and had the same consequence.
    """
    sources = frontend_sources()
    schema = application.state.db.execute(
        "select sql from sqlite_master where type = 'table' and name = 'damage_reports'"
    ).fetchone()["sql"]

    # The haystacks first, both of them. "No copy disagreed" is worth nothing without "the
    # copies are there" — the fourth lessons row, over a schema read and a directory walk.
    found = [
        tuple(int(point) for point in call.replace(" ", "").replace("\n", "").split(","))
        for call in CHAR_CALL.findall(schema)
    ]
    assert found, "no whitespace alphabet in damage_reports at all"
    listed = [
        (path, BLANK_LIST.search(text)) for path, text in sources.items() if BLANK_LIST.search(text)
    ]
    assert len(listed) == 1, f"the browser's alphabet has {len(listed)} homes, not one: {listed}"

    full = tuple(dispatch.BLANK_CODEPOINTS)
    without_the_space = tuple(point for point in full if point != 0x20)
    assert set(found) == {full, without_the_space}, (
        "the schema and store disagree about what is blank; the difference is which characters "
        "a dismissal reason and a neighbourhood may be made of"
    )

    browser = tuple(
        int(value, 16)
        for value in listed[0][1].group(1).replace("\n", "").split(",")
        if value.strip()
    )
    assert browser == full, (
        f"{listed[0][0].name} calls {len(browser)} characters blank and the store calls "
        f"{len(full)} — the layer that disagrees decides nothing, and it is the strictest one "
        "that hides the hole"
    )


def test_the_browser_bounds_a_dismissal_reason_at_the_number_the_store_does(application):
    """**The bound's third and fourth copies, and nothing that failed when they moved.**

    The schema and `dispatch.DISMISSAL_REASON_MAX` were tied by the test above this one.
    `frontend/lib/api.ts` held a third copy described in its own comment as *mirrored*, with
    nothing mirroring it, and `e2e/TASK-008.spec.ts` held a fourth as the literal
    `'N'.repeat(2001)`. Set the third to `8` and `tsc`, `lint`, `build` and all 36 browser specs
    passed while the field stopped a dispatcher at eight characters — and the one browser case
    that exercises the bound removes the `maxlength` attribute before typing, so it could not
    see the change by construction.

    The number now has one definition in the browser half and this is what says so.
    """
    sources = frontend_sources()

    defined = {
        path: [int(value) for value in FRONTEND_BOUND.findall(text)]
        for path, text in sources.items()
        if FRONTEND_BOUND.findall(text)
    }
    assert len(defined) == 1, (
        f"the browser's bound has {len(defined)} definitions, not one: "
        f"{[path.name for path in defined]}"
    )
    path, values = next(iter(defined.items()))
    assert values == [dispatch.DISMISSAL_REASON_MAX] * len(values), (
        f"{path.name} caps a dismissal reason at {values} and the store refuses at "
        f"{dispatch.DISMISSAL_REASON_MAX} — a dispatcher's sentence is silently the shorter one"
    )
    # The haystack: the value has to be reachable from the field and from the browser case, or
    # "one definition" is satisfied by a constant nobody imports.
    assert any(
        "DISMISSAL_REASON_MAX" in text and other != path for other, text in sources.items()
    ), "nothing in the browser half reads the bound, so tying it proves nothing"


BOUND = re.compile(r"length\(dismissed_reason\)\s*<=\s*(\d+)")


def test_one_bound_governs_a_dismissal_reason(application):
    """The bound is in two places — the schema and `dispatch.DISMISSAL_REASON_MAX` — and this is
    what ties them.

    Migration 009 shipped the same shape untied: schema at 120 beside a service constant at
    5000 turns the `400 validation_error` the contract specifies into a `500 internal_error`,
    and the whole suite stayed green through exactly that mutation (CHG-023).

    Written as `<=` rather than `between 1 and N` on purpose, which is migration 012's reason
    reused: `damage_reports` already carries one `between 1 and 120` for the neighbourhood, and
    UTEST-012 reads *every* such bound out of this table and requires them all to be 120. A
    second `between` here would make that test unable to tell one bound from the other.
    """
    schema = {
        row["name"]: row["sql"]
        for row in application.state.db.execute(
            "select name, sql from sqlite_master where type = 'table'"
        )
    }

    # The haystack first: "no bound disagreed" is worth nothing without "a bound is there".
    assert "damage_reports" in schema
    found = [int(value) for value in BOUND.findall(schema["damage_reports"])]
    assert found, "no dismissal-reason bound in the schema at all"
    assert found == [dispatch.DISMISSAL_REASON_MAX] * len(found), (
        f"the schema bounds a dismissal reason at {found} and the service refuses at "
        f"{dispatch.DISMISSAL_REASON_MAX} — the endpoint's 400 becomes a 500 between them"
    )


# ---------------------------------------------------------------------------------------------
# One action, through the endpoint
# ---------------------------------------------------------------------------------------------


def test_one_request_dismisses_a_false_alarm(client, application, accounts):
    """The normal case as a dispatcher meets it: **one action** (REQ-F-008, US-010).

    The board before and after is part of the claim — the report leaves the working list and the
    job it was filed against keeps its location and reads *explained* rather than *empty*
    (CHG-020).
    """
    scenario_id, report_id = a_filed_report(client, application, accounts)
    before = client.get(f"/api/v1/scenarios/{scenario_id}/jobs").json()
    assert before["report_count"] == 1 and before["dismissed_report_count"] == 0

    dismissed = client.post(
        f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": A_REASON}
    )

    assert dismissed.status_code == 201, dismissed.text
    body = dismissed.json()
    assert body["report_id"] == report_id
    assert body["status"] == "dismissed"
    assert body["dismissed_by"] == accounts["user"]["id"]
    assert body["dismissed_reason"] == A_REASON

    after = client.get(f"/api/v1/scenarios/{scenario_id}/jobs").json()
    assert after["report_count"] == 0
    assert after["dismissed_report_count"] == 1
    assert after["job_count"] == 1, "dismissing an alarm does not cancel the job it was filed at"
    assert after["items"][0]["location"] == {"neighbourhood": "Northgate"}


def test_the_reason_is_stored_trimmed_and_a_single_character_is_enough(
    client, application, accounts
):
    """The edge case at the endpoint. `' x '` is stored as `'x'` — one spelling — and it is
    accepted, because the rule is that a reason exists, not that it is long."""
    _, report_id = a_filed_report(client, application, accounts)

    response = client.post(
        f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": "  x  "}
    )

    assert response.status_code == 201, response.text
    assert response.json()["dismissed_reason"] == "x"
    assert stored(application.state.db, report_id)["dismissed_reason"] == "x"


@pytest.mark.parametrize("body", [{}, {"reason": None}, {"reason": ""}, {"reason": "   "},
                                  {"reason": "\t\n"}])
def test_the_endpoint_refuses_an_anonymous_dismissal_and_writes_nothing(
    client, application, accounts, body
):
    """The failure case at the endpoint: a `400`, and the report is still open.

    *Nothing written* is the load-bearing half. A refusal that had already marked the report
    dismissed would satisfy the status code and lose the alarm.
    """
    _, report_id = a_filed_report(client, application, accounts)

    refused = client.post(f"/api/v1/damage-reports/{report_id}/dismiss", json=body)

    assert refused.status_code == 400, refused.text
    assert refused.json()["code"] == "validation_error"
    row = stored(application.state.db, report_id)
    assert (row["status"], row["dismissed_by"], row["dismissed_reason"]) == ("open", None, None)


def test_an_over_length_reason_is_a_400_and_not_a_500(client, application, accounts):
    """The caller's side of the bound tie. A reason one character over the limit is a caller
    mistake and must be answered as one; a `500` says the platform broke, which sends a
    dispatcher to the wrong person during a storm."""
    _, report_id = a_filed_report(client, application, accounts)

    refused = client.post(
        f"/api/v1/damage-reports/{report_id}/dismiss",
        json={"reason": "N" * (dispatch.DISMISSAL_REASON_MAX + 1)},
    )
    accepted = client.post(
        f"/api/v1/damage-reports/{report_id}/dismiss",
        json={"reason": "N" * dispatch.DISMISSAL_REASON_MAX},
    )

    assert refused.status_code == 400, refused.text
    # The permitted side beside it, so "refuses over-length" is not satisfied by refusing
    # everything long.
    assert accepted.status_code == 201, accepted.text


def test_the_endpoint_refuses_an_unknown_field_outright(client, application, accounts):
    """`extra="forbid"`, the CON-003 boundary in the API layer. A caller who sends a street is
    told, and nothing is written — dropping it quietly teaches the sender that the field was
    accepted, and the next caller stores it somewhere else."""
    _, report_id = a_filed_report(client, application, accounts)

    refused = client.post(
        f"/api/v1/damage-reports/{report_id}/dismiss",
        json={"reason": A_REASON, "address": "14 Harbour Street"},
    )

    assert refused.status_code == 400, refused.text
    assert stored(application.state.db, report_id)["status"] == "open"


def test_an_unknown_report_is_a_404_that_names_which_refusal(client, application, accounts):
    """A status code is a category. This endpoint has one `404` today and a second refusal a
    caller could confuse it with — so the test reads the sentence, not the number, the way
    TASK-007's endpoint test had to be rewritten to."""
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    a_storm(application, accounts)

    refused = client.post("/api/v1/damage-reports/DR-nothing/dismiss", json={"reason": A_REASON})

    assert refused.status_code == 404
    assert refused.json()["code"] == "not_found"
    assert "report" in refused.json()["message"].lower()


def test_a_second_dismissal_is_a_409_that_names_the_first(client, application, accounts):
    """BR-004's shape, one table over: a second dismissal is a conflict, never an overwrite.

    The first row must be **byte-identical** afterwards, and there must still be exactly one
    record of it — a retrying client cannot produce two audit rows for one human decision, and
    cannot quietly put its own name on somebody else's.
    """
    scenario_id, report_id = a_filed_report(client, application, accounts)
    first = client.post(
        f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": A_REASON}
    )
    assert first.status_code == 201, first.text
    before = dict(stored(application.state.db, report_id))

    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    second = client.post(
        f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": "Mine now"}
    )

    assert second.status_code == 409, second.text
    assert second.json()["code"] == "conflict"
    assert "already" in second.json()["message"].lower()
    assert dict(stored(application.state.db, report_id)) == before
    assert application.state.db.execute(
        "select count(*) from decision_records where kind = 'dismiss'"
    ).fetchone()[0] == 1


@pytest.mark.parametrize("role", ["user", "admin"])
def test_both_roles_may_dismiss_a_false_alarm(client, application, accounts, role):
    """`technical-spec.md` §7.2 and `security-specification.md`: *Dismiss a false alarm — Admin
    yes, User yes.* The deny path is *signed out* and nothing else, which STEST-001 already
    asserts for this endpoint's row."""
    sign_in(client, accounts[role]["email"], accounts[role]["password"])
    scenario_id = a_storm(application, accounts)
    report_id = file_report(client, scenario_id, "Harbour West")

    response = client.post(
        f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": A_REASON}
    )

    assert response.status_code == 201, response.text
    assert response.json()["dismissed_by"] == accounts[role]["id"]


def test_dismissing_sends_nobody_anywhere(client, application, accounts, caplog):
    """BR-001. Clearing a false alarm records something; it cancels no work, closes no repair
    job and reaches nothing outside the platform. The log line says so in the same words the
    placement endpoint uses, because the one thing a reader of it must not conclude is that
    something was sent somewhere."""
    caplog.set_level(logging.DEBUG)
    scenario_id, report_id = a_filed_report(client, application, accounts)
    job_before = dict(
        application.state.db.execute("select * from repair_jobs").fetchone()
    )
    caplog.clear()

    client.post(f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": A_REASON})
    logged = everything_logged(caplog)

    assert "DAMAGE_REPORT_DISMISSED" in logged
    assert "outcome=recorded_not_dispatched" in logged
    # The dispatcher's own words are not logged, for the reason the placement note is not: they
    # are somebody's sentence about a live storm, and the audit row is where they belong.
    assert A_REASON not in logged
    job_after = dict(application.state.db.execute("select * from repair_jobs").fetchone())
    assert job_after["status"] == job_before["status"] == "pending"


def an_asset(application, scenario_id, asset_id):
    """An asset in this storm, so a report can name one and the per-asset figure can differ."""
    application.state.db.execute(
        "insert into assets (id, scenario_id, external_ids, type, location, match_status,"
        " condition_estimated, created_at)"
        " values (?, ?, '[\"X\"]', 'pump', '{\"lat\": 33.7412, \"lon\": -118.4991}', 'matched',"
        " 0, '2026-08-16T00:00:00Z')",
        (asset_id, scenario_id),
    )
    application.state.db.commit()
    return asset_id


def test_the_dismissal_logs_the_areas_figure_and_neither_of_its_neighbours(
    client, application, accounts, caplog
):
    """**REQ-NF-007 at the second call site, which is the one nothing asserted.**

    `open_reports_in_area` has two callers. `api/dispatch.py`'s is covered by UTEST-012's
    three-way fixture, which names all three answers and asserts the wrong two absent. This one
    — added by TASK-008 — was covered by nothing: `test_dismissing_sends_nobody_anywhere` reads
    the same log line for its event name and its `outcome` and says nothing about the number, so
    replacing the call with a whole-storm count left all 499 tests green. Mutating the shared
    function is red because UTEST-012 covers it; mutating **this call site** was invisible, which
    is the distinction — a discipline that is real in one module and stops at its boundary.

    Three numbers that are all different, after the dismissal: **4** open in the storm, **2** in
    Northgate, **1** for the asset one of them names. The coarser answer and the finer one are
    both asserted **absent**.
    """
    caplog.set_level(logging.DEBUG)
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    scenario_id = a_storm(application, accounts)
    named = an_asset(application, scenario_id, "AS-north-1")

    filed = [
        file_report_naming(client, scenario_id, "Northgate", named),
        file_report_naming(client, scenario_id, "Northgate", None),
        file_report_naming(client, scenario_id, "Northgate", None),
        file_report_naming(client, scenario_id, "Harbour West", None),
        file_report_naming(client, scenario_id, "Saltmarsh", None),
    ]
    caplog.clear()

    dismissed = client.post(
        f"/api/v1/damage-reports/{filed[2]}/dismiss", json={"reason": A_REASON}
    )
    assert dismissed.status_code == 201, dismissed.text
    logged = everything_logged(caplog)

    connection = application.state.db
    assert connection.execute(
        "select count(*) from damage_reports where scenario_id = ? and status = 'open'",
        (scenario_id,),
    ).fetchone()[0] == 4, "four open in the storm, so the storm figure is a different number"
    assert connection.execute(
        "select count(*) from damage_reports where scenario_id = ? and asset_id = ?"
        " and status = 'open'",
        (scenario_id, named),
    ).fetchone()[0] == 1, "and one of them names the asset, so that figure differs too"

    assert "DAMAGE_REPORT_DISMISSED" in logged
    assert "open_reports_in_area=2" in logged
    assert "open_reports_in_area=4" not in logged, "that is the storm, not the neighbourhood"
    assert "open_reports_in_area=1" not in logged, "that is one asset, not the neighbourhood"
    assert "open_reports_in_area=3" not in logged, (
        "that is the area before the dismissal — the figure has to be read after the write, or "
        "it describes a board nobody is looking at"
    )
    for forbidden in ("street", "avenue", "meter", "account", "33.7", "-118.5"):
        assert forbidden not in logged


# ---------------------------------------------------------------------------------------------
# The append-only record of the dismissal (CHG-035)
# ---------------------------------------------------------------------------------------------


def dismiss_record(connection):
    return connection.execute(
        "select * from decision_records where kind = 'dismiss' order by seq"
    ).fetchall()


def test_a_dismissal_appends_exactly_one_row_to_the_decision_record(
    client, application, accounts
):
    """AC-008: *given **any** recommendation or human decision, a row is appended carrying the
    timestamp and the acting user.* A dismissal is a human decision, and `decision_records.kind`
    has permitted `'dismiss'` since migration 006 with nothing writing one (CHG-035).

    The payload carries the reason and the neighbourhood **because the audit row outlives the
    report** — `decision_records` deliberately does not cascade with its scenario (migration
    006), so a row that only pointed at the report would say nothing once the storm was deleted.
    """
    scenario_id, report_id = a_filed_report(client, application, accounts)

    client.post(f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": A_REASON})

    rows = dismiss_record(application.state.db)
    assert len(rows) == 1
    row = rows[0]
    assert row["scenario_id"] == scenario_id
    assert row["subject_type"] == "damage_report"
    assert row["subject_id"] == report_id
    assert row["actor_user_id"] == accounts["user"]["id"]
    assert row["occurred_at"]
    payload = json.loads(row["payload"])
    assert payload["reason"] == A_REASON
    assert payload["neighbourhood"] == "Northgate"
    assert payload["repair_job_id"] == stored(application.state.db, report_id)["repair_job_id"]


def test_the_decision_record_reader_serves_the_dismissal(client, application, accounts):
    """**CHG-035's diagnosis was *no writer, no reader and no decided shape*. TASK-008 built the
    writer and the shape and nothing asked the reader.**

    `GET /api/v1/scenarios/{id}/decisions` is admin-only and `technical-spec.md` calls it *the
    artefact produced to a regulator afterwards* (REQ-F-009). Eleven tests call it; every one of
    them calls it for a `recommendation`, an `accept`/`change`/`reject` or a `placement`. Adding
    `and kind <> 'dismiss'` to `decisions.read_all` left all 499 green while every cleared false
    alarm was silently absent from the record as anybody outside the database reads it — and
    AC-008 is about **any** human decision, so the one kind this task exists to create is the one
    the reader had never been asked for.

    *Prove the haystack is a haystack before reporting no needle*, with the halves reversed: the
    writer was proven and the reader was not.
    """
    scenario_id, report_id = a_filed_report(client, application, accounts)
    dismissed = client.post(
        f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": A_REASON}
    )
    assert dismissed.status_code == 201, dismissed.text
    record_id = dismissed.json()["dismissal_id"]

    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    response = client.get(f"/api/v1/scenarios/{scenario_id}/decisions")

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [item["id"] for item in items] == [record_id], (
        "one human decision has happened in this storm and the record must carry it"
    )
    served = items[0]
    assert served["kind"] == "dismiss"
    assert served["subject_type"] == "damage_report"
    assert served["subject_id"] == report_id
    assert served["actor_user_id"] == accounts["user"]["id"]
    assert served["occurred_at"]
    assert served["payload"]["reason"] == A_REASON
    assert served["payload"]["neighbourhood"] == "Northgate"


def test_the_dismissal_record_cannot_be_altered_or_removed(client, application, accounts):
    """BR-004 on the row this task writes. FF-004 proves the table refuses; this proves it for
    the kind that did not exist when FF-004 was wired."""
    _, report_id = a_filed_report(client, application, accounts)
    client.post(f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": A_REASON})
    connection = application.state.db
    record_id = dismiss_record(connection)[0]["id"]

    for statement in (
        "update decision_records set payload = '{}' where id = ?",
        "delete from decision_records where id = ?",
    ):
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(statement, (record_id,))
            connection.commit()
        connection.rollback()

    assert len(dismiss_record(connection)) == 1


def insert_dismiss_record(connection, *, scenario_id, report_id, actor, payload,
                          subject_type="damage_report", seq=9100):
    connection.execute(
        "insert into decision_records"
        " (id, scenario_id, occurred_at, actor_user_id, kind, subject_type, subject_id, payload,"
        " seq)"
        " values (?, ?, '2026-08-16T00:00:00Z', ?, 'dismiss', ?, ?, ?, ?)",
        (
            f"DR-direct-{seq}",
            scenario_id,
            actor,
            subject_type,
            report_id,
            json.dumps(payload),
            seq,
        ),
    )


def a_dismissed_report(client, application, accounts, neighbourhood="Northgate"):
    """One report, dismissed **directly against the database**, and the payload that truthfully
    describes it — with **no audit row of its own yet**.

    It used to be dismissed through the endpoint, which appends that row. Since CHG-036 the store
    holds *one human decision, one audit row*, so going through the endpoint would make every
    case below a **second** row for one decision, and the permitted control beneath would be
    asserting that the store accepts two of them. That is precisely what this file used to
    require — `assert len(dismiss_record(connection)) == 2` — and the review found it standing
    between the repository and the fix. Dismissing by statement leaves the audit row to be the
    thing under test, which is what these cases are about.
    """
    scenario_id, report_id = a_filed_report(client, application, accounts, neighbourhood)
    connection = application.state.db
    dismiss_directly(connection, report_id, actor=accounts["user"]["id"], reason=A_REASON)
    connection.commit()
    report = stored(connection, report_id)
    assert dismiss_record(connection) == [], "the statement above writes no audit row"
    return scenario_id, report, {
        "reason": A_REASON,
        "neighbourhood": neighbourhood,
        "repair_job_id": report["repair_job_id"],
    }


def test_the_store_accepts_a_dismissal_record_that_agrees_with_its_report(
    client, application, accounts
):
    """The permitted shape, issued directly. Without it, every refusal below is satisfied by a
    trigger that refuses every `dismiss` row."""
    scenario_id, report, payload = a_dismissed_report(client, application, accounts)
    connection = application.state.db

    insert_dismiss_record(
        connection,
        scenario_id=scenario_id,
        report_id=report["id"],
        actor=accounts["user"]["id"],
        payload=payload,
    )
    connection.commit()

    assert len(dismiss_record(connection)) == 1


def test_the_store_refuses_a_second_audit_row_for_one_dismissal(client, application, accounts):
    """**One human decision, one audit row — and the store is what says so** (CHG-036).

    Done criterion 7 is *"exactly one `decision_records` row of kind `dismiss` is appended"*, and
    until this index the rule had two homes and both were service code: `api/dismissals.py`'s
    `409` branch and `dismiss_report`'s `where id = ? and status <> ?`. Neither is the guarantee.
    `damage_reports_dismissal_is_final` refuses a *different* second dismissal and accepts an
    **identical** one — the `update` changes nothing, the trigger stays quiet, and the second
    audit row agrees with the report in every particular, so `decision_records_dismiss_shape`
    accepts it too. With both service guards removed the table held **2** rows for one human
    decision and the whole gate was green.

    Two controls beside it, because a guard that refuses everything is not a guard:
    a **second report** gets its own dismissal record, and **another kind** may still carry
    several rows under one subject — a ranking is re-read and re-recommended, and CHG-029's
    placements are many per ranking on purpose.
    """
    scenario_id, report_id = a_filed_report(client, application, accounts)
    dismissed = client.post(
        f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": A_REASON}
    )
    assert dismissed.status_code == 201, dismissed.text
    connection = application.state.db
    report = stored(connection, report_id)
    agrees = {
        "reason": A_REASON,
        "neighbourhood": "Northgate",
        "repair_job_id": report["repair_job_id"],
    }

    with pytest.raises(sqlite3.IntegrityError, match=ONE_AUDIT_ROW):
        insert_dismiss_record(
            connection,
            scenario_id=scenario_id,
            report_id=report_id,
            actor=accounts["user"]["id"],
            payload=agrees,
            seq=9200,
        )
    connection.rollback()
    assert len(dismiss_record(connection)) == 1

    # A different report is a different decision.
    second = file_report(client, scenario_id, "Saltmarsh")
    assert client.post(
        f"/api/v1/damage-reports/{second}/dismiss", json={"reason": A_REASON}
    ).status_code == 201
    assert len(dismiss_record(connection)) == 2

    # And the index is partial: every other kind is untouched by it.
    for _ in range(2):
        decisions.append_recommendation(
            connection, scenario_id=scenario_id, forecast_revision=0, payload={"items": []}
        )
    assert connection.execute(
        "select count(*) from decision_records where kind = 'recommendation'"
        " and subject_id = ?",
        (decisions.ranking_subject(scenario_id, 0),),
    ).fetchone()[0] == 2


def test_an_identical_retry_is_one_dismissal_and_one_audit_row(client, application, accounts):
    """**The retry no test in this repository ever issued** (CHG-036).

    `test_a_second_dismissal_is_a_409_that_names_the_first` retries with *different* words, which
    is the half `damage_reports_dismissal_is_final` refuses on its own. A client that simply sends
    the same request twice — a dropped response, a double press, a proxy retry — is the case the
    endpoint's own comment says the `409` exists for, and it was the one nothing covered: with the
    two service guards removed it was answered **`201` twice** and left two audit rows.
    """
    scenario_id, report_id = a_filed_report(client, application, accounts)
    first = client.post(
        f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": A_REASON}
    )
    assert first.status_code == 201, first.text
    connection = application.state.db
    before = dict(stored(connection, report_id))

    again = client.post(
        f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": A_REASON}
    )

    assert again.status_code == 409, again.text
    assert again.json()["code"] == "conflict"
    assert "already" in again.json()["message"].lower()
    assert dict(stored(connection, report_id)) == before
    assert len(dismiss_record(connection)) == 1


def test_the_store_refuses_a_dismissal_record_for_a_report_nobody_dismissed(
    client, application, accounts
):
    """The load-bearing clause: **membership, not existence.** A row claiming somebody dismissed
    a report that is still open is an audit trail asserting something that did not happen — and
    an audit trail its own subjects can contradict proves nothing (BR-004's reason for existing).
    """
    scenario_id, report, payload = a_dismissed_report(client, application, accounts)
    connection = application.state.db
    still_open = file_report(client, scenario_id, "Saltmarsh")

    with pytest.raises(sqlite3.IntegrityError, match=AGREES_WITH_THE_REPORT):
        insert_dismiss_record(
            connection,
            scenario_id=scenario_id,
            report_id=still_open,
            actor=accounts["user"]["id"],
            payload={**payload, "neighbourhood": "Saltmarsh"},
            seq=9101,
        )
    connection.rollback()


@pytest.mark.parametrize(
    "field,value",
    [
        ("reason", "Something else entirely"),
        ("neighbourhood", "Saltmarsh"),
        ("repair_job_id", None),
    ],
)
def test_the_store_refuses_a_dismissal_record_that_disagrees_with_its_report(
    client, application, accounts, field, value
):
    """Two stored copies of one fact are two facts the day they disagree (CHG-017's argument).
    The copy in the audit row exists because it must outlive the report — so the store requires
    it to have been true of the report at the moment it was written.

    One field differs per case, and the accepted control is the test above.
    """
    scenario_id, report, payload = a_dismissed_report(client, application, accounts)
    connection = application.state.db

    with pytest.raises(sqlite3.IntegrityError, match=AGREES_WITH_THE_REPORT):
        insert_dismiss_record(
            connection,
            scenario_id=scenario_id,
            report_id=report["id"],
            actor=accounts["user"]["id"],
            payload={**payload, field: value},
            seq=9102,
        )
    connection.rollback()


def test_the_store_refuses_a_dismissal_record_filed_under_another_storm(
    client, application, accounts
):
    """**The clause nothing had ever read back**, and the one the whole product is scoped by.

    `and r.scenario_id = new.scenario_id` is the seventh clause of the `exists`, and every other
    `insert_dismiss_record` call in this file passes the report's own storm — so deleting the
    clause left all 499 tests green while a `dismiss` row naming storm A's report was accepted
    under storm B, served in storm B's `GET /decisions`, and served in storm A's as well.
    *Two storms blended into one ranking would look entirely plausible* is what CLAUDE.md calls
    a correctness bug, and this clause was the only thing preventing it.

    The accepted control is the same row under the report's own storm, one test above.
    """
    scenario_id, report, payload = a_dismissed_report(client, application, accounts)
    connection = application.state.db
    another = a_storm(
        application, accounts, scenario_id="SC-elsewhere", seq=801, content_key="a" * 64
    )

    with pytest.raises(sqlite3.IntegrityError, match=AGREES_WITH_THE_REPORT):
        insert_dismiss_record(
            connection,
            scenario_id=another,
            report_id=report["id"],
            actor=accounts["user"]["id"],
            payload=payload,
            seq=9106,
        )
    connection.rollback()

    assert connection.execute(
        "select count(*) from decision_records where scenario_id = ?", (another,)
    ).fetchone()[0] == 0, "the other storm's record is empty, so nothing was blended into it"
    assert scenario_id != another


def test_a_report_that_belongs_to_no_repair_job_can_be_dismissed(client, application, accounts):
    """**The state the `coalesce` clause was written for, which nothing had ever put it in**
    (CHG-022).

    `decision_records_dismiss_shape` ends `coalesce(r.repair_job_id, '') = coalesce(json_extract
    (new.payload, '$.repair_job_id'), '')`, and the migration says why: *a report may legitimately
    belong to none and `null = null` is null, which a `where` clause reads as false — the row that
    most needs to be recordable would be the one refused.* Replacing both `coalesce`s with plain
    equality left **all 499** tests green, because UTEST-011 fed the clause only its violating
    direction: the `("repair_job_id", None)` case, against a report that *has* a job. No test
    anywhere dismissed a report with no repair job at all.

    Under that mutation this request is a `500`, the alarm stays on the board, and
    `DispatchBoard`'s `Unattached` section goes on drawing a `DismissAlarmControl` on every one
    of them — a control offered for an action whose only possible answer is a refusal, which is
    the TASK-006 defect one screen over.
    """
    scenario_id, _ = a_filed_report(client, application, accounts)
    orphan = an_unattached_report(application, scenario_id)
    before = client.get(f"/api/v1/scenarios/{scenario_id}/jobs").json()
    assert [item["report_id"] for item in before["unattached_reports"]] == [orphan], (
        "the board offers the control on this report, so the board is the haystack"
    )

    response = client.post(
        f"/api/v1/damage-reports/{orphan}/dismiss", json={"reason": A_REASON}
    )

    assert response.status_code == 201, response.text
    assert response.json()["repair_job_id"] is None
    connection = application.state.db
    rows = dismiss_record(connection)
    assert len(rows) == 1
    assert json.loads(rows[0]["payload"])["repair_job_id"] is None
    assert json.loads(rows[0]["payload"])["neighbourhood"] == "Fen Causeway"

    after = client.get(f"/api/v1/scenarios/{scenario_id}/jobs").json()
    assert after["unattached_reports"] == []
    assert after["dismissed_report_count"] == 1
    assert after["job_count"] == before["job_count"], "clearing it cancelled no work (BR-001)"


def test_the_store_refuses_a_dismissal_record_claiming_a_job_the_report_has_not(
    client, application, accounts
):
    """The other direction of the same clause, in the state above. `coalesce` makes *no job* a
    recordable fact; it must not make *no job* agree with *some job*, which is what a bare
    `coalesce(..., '')` on one side alone would do."""
    scenario_id, _ = a_filed_report(client, application, accounts)
    orphan = an_unattached_report(application, scenario_id)
    connection = application.state.db
    dismiss_directly(connection, orphan, actor=accounts["user"]["id"], reason=A_REASON)
    connection.commit()
    a_real_job = connection.execute("select id from repair_jobs limit 1").fetchone()["id"]

    with pytest.raises(sqlite3.IntegrityError, match=AGREES_WITH_THE_REPORT):
        insert_dismiss_record(
            connection,
            scenario_id=scenario_id,
            report_id=orphan,
            actor=accounts["user"]["id"],
            payload={
                "reason": A_REASON,
                "neighbourhood": "Fen Causeway",
                "repair_job_id": a_real_job,
            },
            seq=9107,
        )
    connection.rollback()

    # And the truthful row is accepted, so the refusal is about the claim and not about the
    # report having no job.
    insert_dismiss_record(
        connection,
        scenario_id=scenario_id,
        report_id=orphan,
        actor=accounts["user"]["id"],
        payload={"reason": A_REASON, "neighbourhood": "Fen Causeway", "repair_job_id": None},
        seq=9108,
    )
    connection.commit()
    assert len(dismiss_record(connection)) == 1


def test_the_store_refuses_a_dismissal_record_naming_another_actor(
    client, application, accounts
):
    """*Who dismissed it* has to be the same person in both places, or the append-only row is
    the one that can be wrong."""
    scenario_id, report, payload = a_dismissed_report(client, application, accounts)
    connection = application.state.db

    with pytest.raises(sqlite3.IntegrityError, match=AGREES_WITH_THE_REPORT):
        insert_dismiss_record(
            connection,
            scenario_id=scenario_id,
            report_id=report["id"],
            actor=accounts["admin"]["id"],
            payload=payload,
            seq=9103,
        )
    connection.rollback()


def test_the_store_refuses_a_dismissal_recorded_against_something_other_than_a_report(
    client, application, accounts
):
    """`subject_type` is what `decision_records_by_subject` is read by, so a dismissal filed
    under `ranking` is a decision nobody looking at the report will ever find."""
    scenario_id, report, payload = a_dismissed_report(client, application, accounts)
    connection = application.state.db

    with pytest.raises(sqlite3.IntegrityError, match=SUBJECT_IS_A_REPORT):
        insert_dismiss_record(
            connection,
            scenario_id=scenario_id,
            report_id=report["id"],
            actor=accounts["user"]["id"],
            payload=payload,
            subject_type="ranking",
            seq=9104,
        )
    connection.rollback()


def test_the_store_refuses_an_actorless_dismissal_record(client, application, accounts):
    """*A decision is always somebody's; only the system's own recommendation is actorless* —
    migration 006's own check, asserted for the kind that had no writer when it was written.

    **Two independent rules refuse this row and the trigger reaches it first**, which is why the
    message read here is the trigger's rather than `CHECK constraint failed`: a `BEFORE INSERT`
    trigger runs before constraint checking, and `r.dismissed_by = null` is never true. Saying
    which one fires is the point — the alternative is an assertion that would go on passing if
    both rules were removed and a third refused the row for an unrelated reason.

    The accepted control is `test_the_store_accepts_a_dismissal_record_that_agrees_with_its_report`:
    the same row with an actor is stored, so this refusal is about the actor and nothing else.
    """
    scenario_id, report, payload = a_dismissed_report(client, application, accounts)
    connection = application.state.db

    with pytest.raises(sqlite3.IntegrityError, match=AGREES_WITH_THE_REPORT):
        insert_dismiss_record(
            connection,
            scenario_id=scenario_id,
            report_id=report["id"],
            actor=None,
            payload=payload,
            seq=9105,
        )
    connection.rollback()


def test_a_dismissal_that_cannot_be_recorded_does_not_happen(
    client, application, accounts, monkeypatch
):
    """One action means one transaction. If the audit row cannot be written, the report is not
    dismissed either — a dismissal nobody can explain afterwards is exactly the anonymous
    dismissal this file exists about.

    The write is failed at the append itself rather than at some layer above it, because the
    only window in which a half-done dismissal can exist is between the `update` and the
    `insert`. FTEST-001 asserts the same property for a partial scenario load and gives the
    reason: the failures that happen *before* the first statement would not notice a missing
    rollback at all.
    """
    _, report_id = a_filed_report(client, application, accounts)
    connection = application.state.db

    def refuse(*_args, **_kwargs):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr("app.store.decisions.append_dismissal", refuse)

    response = client.post(
        f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": A_REASON}
    )

    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    row = stored(connection, report_id)
    assert (row["status"], row["dismissed_by"], row["dismissed_reason"]) == ("open", None, None)
    assert dismiss_record(connection) == []


# ---------------------------------------------------------------------------------------------
# A dismissal is written once (CHG-034)
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "statement,parameter",
    [
        ("update damage_reports set dismissed_reason = ? where id = ?", "Never mind"),
        ("update damage_reports set dismissed_by = ? where id = ?", None),
        ("update damage_reports set status = ? where id = ?", "open"),
    ],
)
def test_the_store_refuses_to_rewrite_a_dismissal(
    client, application, accounts, statement, parameter
):
    """*A dismissed report carries who dismissed it and why* (`database-design.md` §1) — and
    without this, it carried whoever wrote it **last**.

    The refusal is read out of its own message rather than off the exception type, because every
    other constraint on this table raises the same class and this test would otherwise go on
    passing for the wrong reason. That has happened six times in this repository.
    """
    _, report_id = a_filed_report(client, application, accounts)
    connection = application.state.db
    client.post(f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": A_REASON})
    before = dict(stored(connection, report_id))

    with pytest.raises(sqlite3.IntegrityError, match=NEVER_REWRITTEN):
        connection.execute(statement, (parameter, report_id))
        connection.commit()
    connection.rollback()

    assert dict(stored(connection, report_id)) == before


def test_a_report_that_is_not_dismissed_can_still_change(client, application, accounts):
    """**The silent case for the trigger.** It must refuse a rewritten dismissal, not every
    update: an open report can still be marked `duplicate`, and a dismissed report's other
    columns are not frozen by this rule. A `when` clause pointed at the wrong status passes the
    tests above and fails these."""
    scenario_id, report_id = a_filed_report(client, application, accounts)
    connection = application.state.db
    second = file_report(client, scenario_id, "Northgate")
    client.post(f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": A_REASON})

    connection.execute("update damage_reports set status = 'duplicate' where id = ?", (second,))
    connection.execute(
        "update damage_reports set reported_by = 'radio-4' where id = ?", (report_id,)
    )
    connection.commit()

    assert stored(connection, second)["status"] == "duplicate"
    assert stored(connection, report_id)["reported_by"] == "radio-4"
    assert stored(connection, report_id)["status"] == "dismissed"


# ---------------------------------------------------------------------------------------------
# Durable (ADR-002)
# ---------------------------------------------------------------------------------------------


def test_the_dismissal_and_its_record_survive_a_restart(tmp_path, monkeypatch):
    """*The database owns everything durable. Nothing that matters lives in process memory, so a
    restart is not an incident* (ADR-002), and `AGENT.md`: **when a task introduces durable
    state, the restart test is part of the task, not part of its review.**

    What is asserted after the restart is the state the restart was supposed to protect — the
    actor, the reason and the audit row — and not merely that the board still renders. A board
    that shows one fewer report would look identical whether the dismissal was durable or the
    report had simply been dropped.
    """
    from app.store import users

    db_path = tmp_path / "restart.db"
    first = build_application(monkeypatch, db_path)
    actor = users.create_user(
        first.state.db,
        name="Dispatcher",
        email="user@sgw.example",
        password=USER_PASSWORD,
        role="operator",
    )
    first.state.db.execute(
        "insert into scenarios (id, name, source_note, content_key, loaded_by, loaded_at,"
        " forecast_revision, seq)"
        " values ('SC-restart', 'Restart storm', 'restart', ?, ?, '2026-08-16T00:00:00Z', 0, 900)",
        ("f" * 64, actor),
    )
    first.state.db.commit()

    with TestClient(first) as opening:
        assert sign_in(opening, "user@sgw.example", USER_PASSWORD).status_code == 201
        report_id = file_report(opening, "SC-restart", "Northgate")
        assert opening.post(
            f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": A_REASON}
        ).status_code == 201
    first.state.db.close()

    second = build_application(monkeypatch, db_path)
    with TestClient(second) as reopened:
        assert sign_in(reopened, "user@sgw.example", USER_PASSWORD).status_code == 201
        row = stored(second.state.db, report_id)
        assert (row["status"], row["dismissed_by"], row["dismissed_reason"]) == (
            "dismissed",
            actor,
            A_REASON,
        )
        records = dismiss_record(second.state.db)
        assert len(records) == 1
        assert json.loads(records[0]["payload"])["reason"] == A_REASON

        # And the rule came back with the data: a restart does not reopen what was cleared.
        again = reopened.post(
            f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": "Mine now"}
        )
        assert again.status_code == 409, again.text
        board = reopened.get("/api/v1/scenarios/SC-restart/jobs").json()
        assert (board["report_count"], board["dismissed_report_count"]) == (0, 1)
    second.state.db.close()
