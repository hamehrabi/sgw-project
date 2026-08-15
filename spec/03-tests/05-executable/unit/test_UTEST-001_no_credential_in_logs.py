"""UTEST-001 — REQ-NF-002, SEC-A-003. Defined in `03-tests/02-functional/unit-tests.md`.

Rule under test: no credential reaches a log or a response.
  normal  — a successful sign-in logs `user_id` only
  edge    — a failed sign-in logs the attempt with no password field
  failure — a password, hash, or session value in any log line or body fails the test

Also covers TASK-001 acceptance criterion 4.
"""

import logging

from conftest import sign_in


def everything_logged(caplog):
    """Message and structured fields alike. A credential in `extra` is still in the log."""
    parts = []
    for record in caplog.records:
        parts.append(record.getMessage())
        parts.extend(
            str(value)
            for key, value in record.__dict__.items()
            if key not in logging.LogRecord("", 0, "", 0, "", (), None).__dict__
        )
    return "\n".join(parts)


def test_a_successful_sign_in_logs_the_user_id_and_no_credential(client, accounts, caplog):
    caplog.set_level(logging.DEBUG)

    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    logged = everything_logged(caplog)

    assert "AUTH_LOGIN_SUCCEEDED" in logged
    assert accounts["admin"]["id"] in logged
    assert accounts["admin"]["password"] not in logged
    assert "$2b$" not in logged


def test_a_successful_sign_in_does_not_log_the_email_address(client, accounts, caplog):
    """`database-design.md` §6: logged only as `user_id`, never the address."""
    caplog.set_level(logging.DEBUG)

    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])

    assert accounts["admin"]["email"] not in everything_logged(caplog)


def test_a_successful_sign_in_does_not_log_the_session_value(client, accounts, caplog):
    caplog.set_level(logging.DEBUG)

    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    logged = everything_logged(caplog)

    for cookie_value in client.cookies.values():
        assert cookie_value not in logged


def test_a_failed_sign_in_logs_the_attempt_without_the_password(client, accounts, caplog):
    caplog.set_level(logging.DEBUG)

    sign_in(client, accounts["admin"]["email"], "a-wrong-password-nobody-should-see")
    logged = everything_logged(caplog)

    assert "AUTH_LOGIN_FAILED" in logged
    assert "a-wrong-password-nobody-should-see" not in logged
    assert accounts["admin"]["email"] not in logged


def test_an_attempt_on_an_unknown_account_logs_no_identifier_either(client, accounts, caplog):
    caplog.set_level(logging.DEBUG)

    sign_in(client, "stranger@sgw.example", "guessing")
    logged = everything_logged(caplog)

    assert "AUTH_LOGIN_FAILED" in logged
    assert "stranger@sgw.example" not in logged
    assert "guessing" not in logged


def test_every_log_line_carries_a_request_id(client, accounts, caplog):
    """`technical-spec.md` §9.6 — related events must be traceable to one request."""
    caplog.set_level(logging.DEBUG)

    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])

    sgw_records = [r for r in caplog.records if r.name.startswith("sgw")]
    assert sgw_records
    for record in sgw_records:
        assert getattr(record, "request_id", None)
