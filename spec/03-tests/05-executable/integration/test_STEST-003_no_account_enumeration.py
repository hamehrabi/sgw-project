"""STEST-003 — SEC-A-001, SEC-A-003. Defined in `03-tests/03-non-functional/security-tests.md`.

Sign in with an unregistered email; then with a wrong password. Expect an **identical**
response for both, and no password, hash, or session value in any response body or error.

Also covers TASK-001 acceptance criterion 2.
"""

from conftest import sign_in


def test_an_unknown_email_and_a_wrong_password_are_indistinguishable(client, accounts):
    unknown = sign_in(client, "nobody@sgw.example", "whatever-this-is")
    wrong = sign_in(client, accounts["admin"]["email"], "not-the-right-password")

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


def test_the_refusal_names_neither_field(client, accounts):
    response = sign_in(client, accounts["admin"]["email"], "not-the-right-password")
    body = response.json()

    assert body["message"] == "The email or password is incorrect."
    # No `field` key: naming one would say which half was wrong, which is the whole
    # thing this test exists to prevent (`security-specification.md` §6).
    assert set(body) == {"code", "message"}


def test_no_credential_appears_in_a_failed_sign_in_response(client, accounts):
    response = sign_in(client, accounts["admin"]["email"], "not-the-right-password")

    assert "not-the-right-password" not in response.text
    assert "$2b$" not in response.text  # a bcrypt hash prefix


def test_no_credential_or_session_value_appears_in_a_successful_sign_in_body(client, accounts):
    response = sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    body = response.json()

    assert response.status_code == 201
    assert accounts["admin"]["password"] not in response.text
    assert "$2b$" not in response.text
    # The session value belongs in the cookie and nowhere else. A body carrying it puts a
    # credential into anything that logs a response.
    assert set(body) == {"user_id", "name", "role", "must_change_password"}
    for cookie_value in client.cookies.values():
        assert cookie_value not in response.text


def test_the_session_cookie_is_not_reachable_from_script(client, accounts):
    response = sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])

    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=strict" in set_cookie


def test_an_unexpected_server_failure_reveals_nothing(client, accounts, monkeypatch):
    """`security-specification.md` §6: a stack trace or database error is never the answer."""
    from app.store import users

    def explode(*args, **kwargs):
        raise RuntimeError("password_hash=$2b$04$somethingsecret database=/srv/app.db")

    monkeypatch.setattr(users, "find_by_email", explode)

    response = sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])

    assert response.status_code == 500
    assert response.json() == {
        "code": "internal_error",
        "message": "Something went wrong. Please try again later.",
    }
    assert "somethingsecret" not in response.text
    assert "app.db" not in response.text
