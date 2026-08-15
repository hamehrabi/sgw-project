"""ATEST-001 — REQ-F-001, AC-001. Defined in `03-tests/02-functional/acceptance-tests.md`.

A prepared scenario whose asset records use different codes for the same asset is loaded.
Each asset appears once; every value shows its source and age; unmatched records are flagged,
not merged.

The read half of defect 1. UTEST-002 proves the loader resolves the codes; this proves the
resolution survives the store and reaches the API in the shape a screen can render — including
the two things BR-003 makes non-optional, source and age, which have no shape to be omitted
from.
"""

from conftest import fixture_files, sign_in


def load_and_read(client, accounts):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    scenario_id = created.json()["scenario_id"]
    return client.get(f"/api/v1/scenarios/{scenario_id}/assets").json()


def test_the_joined_view_is_readable(client, accounts):
    body = load_and_read(client, accounts)

    assert body["items"]


def test_each_asset_appears_exactly_once(client, accounts):
    body = load_and_read(client, accounts)

    carrying_ss1042 = [i for i in body["items"] if "SS-1042" in i["external_ids"]]

    assert len(carrying_ss1042) == 1
    assert "TX-4471" in carrying_ss1042[0]["external_ids"]


def test_every_value_carries_its_source_and_its_age(client, accounts):
    """BR-003. There is no shape of this response without them."""
    body = load_and_read(client, accounts)

    for item in body["items"]:
        for value in item["values"]:
            assert set(value) >= {"name", "value", "source", "observed_at", "estimated"}


def test_a_condition_value_names_where_it_came_from_and_when(client, accounts):
    body = load_and_read(client, accounts)

    northgate = next(i for i in body["items"] if "SS-1042" in i["external_ids"])
    condition = next(v for v in northgate["values"] if v["name"] == "condition")

    assert condition["value"] == "3"
    assert condition["source"] == "inspection"
    assert condition["observed_at"] == "2026-06-02"


def test_an_estimated_value_is_marked_distinctly_from_a_measured_one(client, accounts):
    """UTEST-004's other half — the distinction has to survive to the API."""
    body = load_and_read(client, accounts)

    ridgeline = next(i for i in body["items"] if "LN-3312" in i["external_ids"])
    condition = next(v for v in ridgeline["values"] if v["name"] == "condition")

    assert condition["estimated"] is True


def test_unmatched_records_are_flagged_and_present(client, accounts):
    """Never merged on a guess, and never dropped — the dangerous half is 'dropped'."""
    body = load_and_read(client, accounts)

    flagged = [i for i in body["items"] if i["match_status"] == "needs_review"]

    assert {"SS-2210", "PS-9001"} <= {c for i in flagged for c in i["external_ids"]}


def test_a_user_role_may_read_the_joined_view(client, accounts):
    """Reading is not privileged; only loading is (REQ-R-001)."""
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    scenario_id = created.json()["scenario_id"]
    client.delete("/api/v1/auth/session")
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])

    assert client.get(f"/api/v1/scenarios/{scenario_id}/assets").status_code == 200
