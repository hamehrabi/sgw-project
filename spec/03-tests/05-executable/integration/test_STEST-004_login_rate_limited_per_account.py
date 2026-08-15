"""STEST-004 — SEC-A-005. Defined in `03-tests/03-non-functional/security-tests.md`.

Six failed attempts on one account within ten minutes, **each from a different address**.
Expect 429 with `Retry-After`. The per-IP limit alone must not be what stops it.

Also covers TASK-001 acceptance criterion 3.

Every attempt below arrives from a different address on purpose. An IP-only limit would see
one attempt per address and let all six through — which is what `runtime-and-scale.md` §1
means by "an IP limit alone is walked past by a distributed attempt".
"""

from fastapi.testclient import TestClient

LIMIT_PER_ACCOUNT = 5  # runtime-and-scale.md §1: 5 per account per 10 minutes


def attempt_from(application, address, email, password):
    client = TestClient(application, client=(address, 51000))
    return client.post("/api/v1/auth/session", json={"email": email, "password": password})


def test_the_sixth_attempt_on_one_account_is_refused_though_every_address_differs(
    application, accounts
):
    email = accounts["admin"]["email"]

    for index in range(LIMIT_PER_ACCOUNT):
        response = attempt_from(application, f"10.0.0.{index + 1}", email, "wrong-password")
        assert response.status_code == 401, f"attempt {index + 1} should still be a plain refusal"

    sixth = attempt_from(application, "10.0.0.6", email, "wrong-password")

    assert sixth.status_code == 429
    assert "retry-after" in sixth.headers
    assert int(sixth.headers["retry-after"]) > 0


def test_the_limit_follows_the_account_not_the_caller(application, accounts):
    """A correct password from a fresh address is still refused once the account is locked."""
    email = accounts["admin"]["email"]
    for index in range(LIMIT_PER_ACCOUNT + 1):
        attempt_from(application, f"10.0.1.{index + 1}", email, "wrong-password")

    response = attempt_from(application, "10.0.1.99", email, accounts["admin"]["password"])

    assert response.status_code == 429


def test_one_account_being_limited_does_not_lock_another(application, accounts):
    """Otherwise anyone could lock the whole control room out during a storm."""
    for index in range(LIMIT_PER_ACCOUNT + 1):
        attempt_from(application, f"10.0.2.{index + 1}", accounts["admin"]["email"], "wrong")

    response = attempt_from(
        application, "10.0.2.99", accounts["user"]["email"], accounts["user"]["password"]
    )

    assert response.status_code == 201


def test_a_successful_sign_in_clears_the_account_count(application, accounts):
    email = accounts["user"]["email"]
    for index in range(LIMIT_PER_ACCOUNT - 1):
        attempt_from(application, f"10.0.3.{index + 1}", email, "wrong-password")

    succeeded = attempt_from(application, "10.0.3.50", email, accounts["user"]["password"])
    assert succeeded.status_code == 201

    # The counter reset, so a fresh run of failures is refused normally rather than at once.
    assert attempt_from(application, "10.0.3.51", email, "wrong-password").status_code == 401


def test_the_refusal_says_nothing_beyond_the_limit(application, accounts):
    email = accounts["admin"]["email"]
    for index in range(LIMIT_PER_ACCOUNT + 1):
        response = attempt_from(application, f"10.0.4.{index + 1}", email, "wrong-password")

    assert response.json() == {
        "code": "too_many_attempts",
        "message": "Too many sign-in attempts. Please try again later.",
    }
