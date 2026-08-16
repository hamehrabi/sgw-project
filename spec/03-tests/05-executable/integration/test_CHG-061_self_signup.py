"""CHG-061 — self-service sign-up, at the client's instruction.

Reverses `security-specification.md` §7's "no endpoint creates an account" for exactly one
shape: a signed-out caller may create an **operator** account and nothing else. The role is
not a parameter — the request model forbids unknown fields — and the platform's one
password policy (12 characters, the CLI's and the password change's) applies here too.
"""

from conftest import sign_in


def test_a_signed_out_visitor_can_create_an_operator_account_and_is_signed_in(client, accounts):
    created = client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Self Service",
            "email": "self.service@sgw.example",
            "password": "a-long-enough-password",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["role"] == "operator", "self-registration never grants admin"
    assert "password_hash" not in created.text
    assert "a-long-enough-password" not in created.text

    # The signup signs the caller in — the identity read answers with the new account.
    identity = client.get("/api/v1/auth/session")
    assert identity.status_code == 200
    assert identity.json()["name"] == "Self Service"
    assert identity.json()["role"] == "operator"


def test_the_role_is_not_a_parameter(client, accounts):
    refused = client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Aspiring Admin",
            "email": "aspiring@sgw.example",
            "password": "a-long-enough-password",
            "role": "admin",
        },
    )
    assert refused.status_code in (400, 422), "an unknown field is refused, not ignored"


def test_a_short_password_is_refused_by_the_same_policy_as_everywhere_else(client, accounts):
    refused = client.post(
        "/api/v1/auth/signup",
        json={"name": "Short", "email": "short@sgw.example", "password": "test"},
    )
    assert refused.status_code == 400
    assert "12" in refused.json()["message"]


def test_a_blank_name_in_the_wide_alphabet_is_refused(client, accounts):
    refused = client.post(
        "/api/v1/auth/signup",
        json={
            "name": "​",  # one zero-width space — CHG-023's alphabet, not str.strip()
            "email": "blank.name@sgw.example",
            "password": "a-long-enough-password",
        },
    )
    assert refused.status_code == 400


def test_a_taken_email_is_refused_and_no_second_account_appears(client, application, accounts):
    taken = accounts["user"]["email"]
    refused = client.post(
        "/api/v1/auth/signup",
        json={"name": "Twin", "email": taken, "password": "a-long-enough-password"},
    )
    assert refused.status_code == 409

    count = application.state.db.execute(
        "select count(*) as n from users where email = ?", (taken,)
    ).fetchone()["n"]
    assert count == 1


def test_the_new_account_cannot_do_admin_things(client, accounts):
    client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Operator Only",
            "email": "operator.only@sgw.example",
            "password": "a-long-enough-password",
        },
    )
    refused = client.post(
        "/api/v1/scenarios",
        data={"name": "Nope", "source_note": "nope"},
        files=[("files", ("manifest.json", b"{}", "application/json"))],
    )
    assert refused.status_code == 403, "an operator cannot load a storm (STEST-005's rule)"

    # And the admin path still works for an admin — the check above is about the role.
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    assert client.get("/api/v1/auth/session").json()["role"] == "admin"
