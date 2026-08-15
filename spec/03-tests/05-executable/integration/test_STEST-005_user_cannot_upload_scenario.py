"""STEST-005 — SEC-Z-002, REQ-R-001. Defined in `03-tests/03-non-functional/security-tests.md`.

A `user` role calls the scenario upload endpoint **directly**, bypassing the interface.
Expect 403, no scenario row, **no file written to disk**, and the refusal recorded in the
**security log** with actor, time, filename and reason (CHG-015).

**The record was going to be a `decision_records` row and is not.** That table holds decisions
about recommendations; a refused upload is an access-control event. Writing it there would have
meant making `scenario_id` nullable — a refused upload has no scenario, because refusing it is
what stopped one existing — and that not-null constraint is part of what makes the audit table
trustworthy. AC-009's wording was corrected rather than the schema loosened.

The interface hides the upload panel from a non-admin. That is why this test calls the
endpoint directly: an interface-driven version would pass while the endpoint stayed open.
"""

import logging

from conftest import fixture_files, sign_in


def upload(client, files=None):
    payload = files if files is not None else fixture_files()
    return client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "prepared fixture"},
        files=[("files", (name, content, "text/csv")) for name, content in payload.items()],
    )


def test_a_signed_out_upload_is_refused(client):
    response = upload(client)

    assert response.status_code == 401


def test_a_user_role_is_refused(client, accounts):
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])

    response = upload(client)

    assert response.status_code == 403


def test_the_refusal_creates_no_scenario(client, application, accounts):
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])

    upload(client)

    assert application.state.db.execute("select count(*) from scenarios").fetchone()[0] == 0


def test_the_refusal_writes_no_file_to_disk(client, application, accounts, env):
    import pathlib

    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])

    upload(client)

    upload_dir = pathlib.Path(env["SCENARIO_UPLOAD_DIR"])
    written = list(upload_dir.rglob("*")) if upload_dir.exists() else []
    assert [p for p in written if p.is_file()] == []


def test_the_refusal_does_not_reveal_what_the_endpoint_accepts(client, accounts):
    """A generic access-denied response (`security-specification.md` §7)."""
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])

    body = upload(client).json()

    assert set(body) == {"code", "message"}
    assert "csv" not in body["message"].lower()
    assert "manifest" not in body["message"].lower()


def test_an_admin_is_not_refused(client, accounts):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])

    assert upload(client).status_code in (200, 201, 202)


def test_the_refusal_is_recorded_in_the_security_log(client, accounts, caplog):
    """AC-009, as corrected by CHG-015: actor, time, filename, reason.

    **In the security log, not the decision record.** That table holds decisions about
    recommendations; a refused upload is an access-control event. Recording it there would
    have required `scenario_id` to be nullable — a refused upload has no scenario — which
    trades the constraint that makes the audit table trustworthy for one event type.
    """
    caplog.set_level(logging.DEBUG)
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])

    upload(client)

    refusals = [r for r in caplog.records if r.getMessage() == "SCENARIO_UPLOAD_REFUSED"]
    assert refusals, "the refusal must be recorded, not merely returned"
    record = refusals[0]
    assert record.user_id == accounts["user"]["id"]
    assert record.reason == "not_admin"
    assert record.outcome == "refused"
    assert "assets.csv" in record.filenames
    assert record.request_id, "traceable to the request that was refused"


def test_the_refusal_record_carries_no_file_contents(client, accounts, caplog):
    """`database-design.md` §6: the contents of an uploaded file are never logged."""
    caplog.set_level(logging.DEBUG)
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])

    upload(client)

    logged = "\n".join(r.getMessage() + str(r.__dict__) for r in caplog.records)
    assert "Northgate Substation" not in logged, "a filename is not the file"
