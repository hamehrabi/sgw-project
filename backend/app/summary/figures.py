"""The fixed set of figures the model is allowed to see (CHG-040).

Assembled from stored rows and nothing else. **This dict is the whole prompt surface**:
what is not in it cannot truthfully appear in a draft, and the verifier holds every draft
to exactly that. Adding a key here widens what a model may say — treat an edit to this
file as an edit to ADR-009's boundary, because it is one.

The top-ranked asset's **name** is here by CHG-040's recorded widening of ADR-009, for the
summary path only.
"""

import json
import sqlite3


def assemble(connection: sqlite3.Connection, scenario_id: str) -> dict:
    scenario = connection.execute(
        "select * from scenarios where id = ?", (scenario_id,)
    ).fetchone()

    open_incidents = connection.execute(
        "select count(*) as n from repair_jobs where scenario_id = ? and status <> 'done'",
        (scenario_id,),
    ).fetchone()["n"]

    critical = connection.execute(
        "select count(distinct a.id) as n"
        " from damage_reports r join assets a on a.id = r.asset_id"
        "   and a.scenario_id = r.scenario_id"
        " where r.scenario_id = ? and r.status = 'open' and a.is_critical_facility = 1",
        (scenario_id,),
    ).fetchone()["n"]

    crews_deployed = connection.execute(
        "select count(distinct json_extract(payload, '$.crew')) as n"
        " from decision_records where scenario_id = ? and kind = 'placement'",
        (scenario_id,),
    ).fetchone()["n"]

    # The operator's own staging plan is the only total that exists — there is no roster.
    # None when nobody has recorded one, and the screen says so rather than inventing 18.
    plan = connection.execute(
        "select depots from crew_staging where scenario_id = ? order by seq desc limit 1",
        (scenario_id,),
    ).fetchone()
    crews_total = (
        sum(depot.get("crews", 0) for depot in json.loads(plan["depots"])) if plan else None
    )

    customers_out = connection.execute(
        # 'open' only: a duplicate is a repeat call about damage already counted (CHG-021),
        # and a dismissed report is a cleared false alarm.
        "select coalesce(sum(customers_out), 0) as n from damage_reports"
        " where scenario_id = ? and status = 'open'",
        (scenario_id,),
    ).fetchone()["n"]

    revision = scenario["forecast_revision"]
    high_risk_count = connection.execute(
        "select count(*) as n from risk_scores"
        " where scenario_id = ? and forecast_revision = ? and band = 'High'",
        (scenario_id, revision),
    ).fetchone()["n"]

    top = connection.execute(
        "select a.name, a.external_ids, rs.reasons from risk_scores rs"
        " join assets a on a.id = rs.asset_id"
        " where rs.scenario_id = ? and rs.forecast_revision = ? and rs.rank = 1",
        (scenario_id, revision),
    ).fetchone()
    top_asset_name = None
    top_asset_impact = None
    if top is not None:
        top_asset_name = top["name"] or json.loads(top["external_ids"])[0]
        reasons = json.loads(top["reasons"])
        if reasons:
            top_asset_impact = reasons[0].get("detail")

    return {
        "storm_name": scenario["name"],
        "open_incidents": open_incidents,
        "critical_facilities_affected": critical,
        "crews_deployed": crews_deployed,
        "crews_total": crews_total,
        "customers_out": customers_out,
        "high_risk_count": high_risk_count,
        "top_asset_name": top_asset_name,
        "top_asset_impact": top_asset_impact,
        "forecast_issued_at": scenario["forecast_issued_at"],
    }
