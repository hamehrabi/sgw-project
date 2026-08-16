"""STEST-001 — SEC-A-001, SEC-Z-001. Defined in `03-tests/03-non-functional/security-tests.md`.

Request any data route with no session. Expect 401 and no body containing scenario data.

Also covers TASK-001 acceptance criterion 1.
"""

import pytest
from conftest import sign_in

# Every data route in the endpoint index (`api-specification.md`). None of them is built
# yet — TASK-002 onward build them — and that is exactly why this test is written now: the
# refusal must come from the API layer's one session check, before routing, so that a route
# added later is refused by default rather than by remembering to guard it.
DATA_ROUTES = [
    # Which storms are loaded is data: it names them, says where they came from and when they
    # arrived. Added by TASK-009 (CHG-030), and named here rather than left to the generic
    # unknown-path case, because the criterion names the endpoint.
    ("GET", "/api/v1/scenarios"),
    ("GET", "/api/v1/scenarios/SCEN-1"),
    ("GET", "/api/v1/scenarios/SCEN-1/assets"),
    ("GET", "/api/v1/scenarios/SCEN-1/risks"),
    ("GET", "/api/v1/scenarios/SCEN-1/jobs"),
    ("GET", "/api/v1/scenarios/SCEN-1/decisions"),
    ("POST", "/api/v1/scenarios"),
    ("POST", "/api/v1/scenarios/SCEN-1/damage-reports"),
    ("POST", "/api/v1/scenarios/SCEN-1/forecast-revisions"),
    ("POST", "/api/v1/scenarios/SCEN-1/placements"),
    ("POST", "/api/v1/recommendations/REC-1/decision"),
    ("POST", "/api/v1/damage-reports/DR-1/dismiss"),
]

# Reachable without a session, and each for a stated reason: the health check has to answer
# during an incident (`runtime-and-scale.md` §1), and sign-in is how anyone gets a session at
# all. Everything else the application publishes must be in the list above.
PUBLIC = {
    ("GET", "/api/v1/health"),
    ("POST", "/api/v1/auth/session"),
    ("GET", "/api/v1/auth/session"),
    ("DELETE", "/api/v1/auth/session"),
}

IDENTIFIERS = {"SCEN-1", "REC-1", "DR-1"}


def shape(path: str) -> str:
    """A path with its identifiers removed, so `/scenarios/{scenario_id}/jobs` from the
    published schema and `/scenarios/SCEN-1/jobs` from the list above are one thing."""
    return "/".join(
        "*" if segment.startswith("{") or segment in IDENTIFIERS else segment
        for segment in path.split("/")
    )


@pytest.mark.parametrize("method,path", DATA_ROUTES)
def test_signed_out_request_to_a_data_route_is_refused(client, method, path):
    response = client.request(method, path)

    assert response.status_code == 401


@pytest.mark.parametrize("method,path", DATA_ROUTES)
def test_the_refusal_body_carries_no_project_data(client, method, path):
    response = client.request(method, path)

    # `code` and `message` and nothing else — the contract rule in `api-specification.md`.
    # A refusal that leaked a scenario, an asset or a rank would satisfy the status code
    # and fail the requirement.
    assert set(response.json()) == {"code", "message"}
    assert response.json()["code"] == "not_authenticated"


def test_every_endpoint_the_application_publishes_is_named_in_this_list(application):
    """**The list has to keep up with the application, and until now nothing made it.**

    `POST /api/v1/scenarios/{id}/damage-reports` was created by TASK-005 (CHG-016) and never
    added here, so done criterion 9's first half — *a signed-out caller reaches neither
    endpoint* — was covered only by the generic unknown-path case. The behaviour held, because
    `SessionGuard` refuses before routing; the criterion names the endpoint, and a row that is
    free is worth having.

    Read from the published schema, not from `application.routes`: that list wraps
    `include_router` in objects whose own `path` is `None`, which is how a check in this
    repository last enumerated four documentation routes and none of the ten endpoints.
    """
    published = {
        (method.upper(), shape(path))
        for path, operations in application.openapi()["paths"].items()
        for method in operations
    }

    # The haystack, before anything is said about the needles: an enumeration that stopped
    # returning endpoints would satisfy every difference below and prove nothing.
    assert ("GET", "/api/v1/scenarios/*/jobs") in published
    assert ("POST", "/api/v1/scenarios/*/damage-reports") in published
    assert len(published) >= 10

    guarded = {(method, shape(path)) for method, path in DATA_ROUTES}
    public = {(method, shape(path)) for method, path in PUBLIC}

    assert not (published - guarded - public), (
        "these endpoints exist and no signed-out test names them: "
        f"{sorted(published - guarded - public)}"
    )


def test_an_unknown_path_is_also_refused_rather_than_reported_missing(client):
    """A 404 here would confirm which endpoints exist to someone who is not signed in."""
    response = client.get("/api/v1/scenarios/SCEN-1/something-nobody-has-built")

    assert response.status_code == 401


def test_the_health_check_stays_reachable_while_signed_out(client):
    """It has to answer during an incident; `runtime-and-scale.md` §1 refuses to gate it."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200


def test_the_sign_in_endpoint_stays_reachable_while_signed_out(client, accounts):
    """Otherwise nobody could ever sign in."""
    response = sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])

    assert response.status_code == 201
