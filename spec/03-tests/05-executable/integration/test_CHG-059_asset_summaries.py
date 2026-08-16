"""CHG-059 — per-asset summaries: generated once, stored, read back without inference.

The cache is the schema's (`unique (scenario_id, asset_id, forecast_revision)`), the
prompt surface excludes the asset's identity, and with the model disabled the endpoint
still answers — the template path is the product working, not a degraded mode.
"""

import json

import pytest
from conftest import fixture_files, sign_in

FIGURE_KEYS = {
    "asset_type",
    "risk_band",
    "rank",
    "ranked_total",
    "reasons",
    "unscored_reason",
    "forecast_issued_at",
}


@pytest.fixture
def loaded(client, accounts):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Summary storm", "source_note": "prepared pack"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    assert created.status_code == 201, created.text
    return created.json()["scenario_id"]


def ranked_assets(client, scenario_id):
    ranking = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    return [item for item in ranking["items"] if item["rank"] is not None]


def test_generated_once_then_served_from_the_store(client, loaded):
    asset = ranked_assets(client, loaded)[0]

    first = client.post(
        f"/api/v1/scenarios/{loaded}/asset-summaries",
        json={"asset_id": asset["asset_id"], "forecast_revision": 0},
    )
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["label"] == "Assembled from computed factors", "no model in the suite"
    assert body["verification"]["ok"] is True
    assert body["text"].strip()
    assert body["forecast_revision"] == 0

    second = client.post(
        f"/api/v1/scenarios/{loaded}/asset-summaries",
        json={"asset_id": asset["asset_id"], "forecast_revision": 0},
    )
    assert second.status_code == 200, "the stored row answers — nothing regenerates"
    assert second.json()["asset_summary_id"] == body["asset_summary_id"]

    listed = client.get(f"/api/v1/scenarios/{loaded}/asset-summaries").json()
    assert listed["scenario_id"] == loaded
    assert any(item["asset_summary_id"] == body["asset_summary_id"] for item in listed["items"])


def test_the_prompt_surface_excludes_the_assets_identity(client, loaded):
    """ADR-009 without CHG-040's widening: no name, no identifier, no coordinate."""
    asset = ranked_assets(client, loaded)[0]
    created = client.post(
        f"/api/v1/scenarios/{loaded}/asset-summaries",
        json={"asset_id": asset["asset_id"], "forecast_revision": 0},
    )
    figures = created.json()["source_figures"]
    assert set(figures) == FIGURE_KEYS

    flattened = json.dumps(figures).lower()
    if asset["name"]:
        assert asset["name"].lower() not in flattened
    for code in asset["external_ids"]:
        assert code.lower() not in flattened
    assert asset["asset_id"].lower() not in flattened
    assert "lat" not in figures and "lon" not in figures


def test_an_asset_this_storm_does_not_hold_is_a_404(client, loaded):
    refused = client.post(
        f"/api/v1/scenarios/{loaded}/asset-summaries",
        json={"asset_id": "AST-does-not-exist", "forecast_revision": 0},
    )
    assert refused.status_code == 404


def test_a_revision_with_no_stored_rank_is_a_404(client, loaded):
    asset = ranked_assets(client, loaded)[0]
    refused = client.post(
        f"/api/v1/scenarios/{loaded}/asset-summaries",
        json={"asset_id": asset["asset_id"], "forecast_revision": 7},
    )
    assert refused.status_code == 404, "a summary describes a ranking that exists"


def test_an_operator_can_generate_and_read_summaries(client, accounts, loaded):
    """Reading the ranking is the product; summarising one row of it is the same act."""
    asset = ranked_assets(client, loaded)[1]
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    created = client.post(
        f"/api/v1/scenarios/{loaded}/asset-summaries",
        json={"asset_id": asset["asset_id"], "forecast_revision": 0},
    )
    assert created.status_code == 201, created.text
    assert client.get(f"/api/v1/scenarios/{loaded}/asset-summaries").status_code == 200
