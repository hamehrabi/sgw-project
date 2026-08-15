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
    ("GET", "/api/v1/scenarios/SCEN-1"),
    ("GET", "/api/v1/scenarios/SCEN-1/assets"),
    ("GET", "/api/v1/scenarios/SCEN-1/risks"),
    ("GET", "/api/v1/scenarios/SCEN-1/jobs"),
    ("GET", "/api/v1/scenarios/SCEN-1/decisions"),
    ("POST", "/api/v1/scenarios"),
    ("POST", "/api/v1/scenarios/SCEN-1/forecast-revisions"),
    ("POST", "/api/v1/scenarios/SCEN-1/placements"),
    ("POST", "/api/v1/recommendations/REC-1/decision"),
    ("POST", "/api/v1/damage-reports/DR-1/dismiss"),
]


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
