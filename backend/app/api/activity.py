"""The activity rail and the movement strip — two reads over what already happened
(CHG-054, CHG-044).

**The feed's wording rule is enforced here, where it can fail, not in a style note**
(CHG-054): every entry is assembled from a stored record's kind and actor, there is no
free-text path into the rail, and no phrasing below says the system flagged, decided,
prioritised or synced anything — because it never did. Human actions name the human;
system events name the event.
"""

import json

from fastapi import APIRouter, Request

from app.api import errors, views
from app.store import movement as movement_store
from app.store import scenarios, security

router = APIRouter(prefix="/api/v1/scenarios", tags=["activity"])

FEED_LIMIT = 30


def _actor_names(connection) -> dict:
    return {row["id"]: row["name"] for row in connection.execute("select id, name from users")}


def _decision_entry(row, names) -> dict | None:
    """One decision record, phrased. Returns None for kinds that are not feed material."""
    actor = names.get(row["actor_user_id"], "Somebody")
    payload = json.loads(row["payload"]) if row["payload"] else {}
    kind = row["kind"]

    if kind == "recommendation":
        # A system EVENT — a ranking was recorded — never a system decision. "The system
        # flagged X" is the sentence this product must never render (CHG-054).
        revision = payload.get("forecast_revision")
        text = (
            f"Ranking recorded at forecast revision {revision}"
            if revision is not None
            else "Ranking recorded"
        )
        return {"kind": "system", "text": text, "occurred_at": row["occurred_at"]}
    if kind in ("accept", "change", "reject"):
        verb = {"accept": "accepted", "change": "asked for a change to", "reject": "rejected"}[
            kind
        ]
        if row["subject_type"] == "asset_ranking":
            # CHG-055, in CHG-054's exact permitted shape: the human, the verb, the
            # asset. "J. Ruiz accepted the ranking for Bayside Substation" — a person
            # deciding, never the system flagging.
            action = payload.get("action", verb)
            code = payload.get("asset_code", "an asset")
            phrased = {
                "Accept": f"{actor} accepted the ranking for {code}",
                "Adjust": f"{actor} adjusted the ranking for {code}",
                "Dismiss": f"{actor} dismissed the ranking for {code}",
            }.get(action, f"{actor} {verb} the ranking for {code}")
            return {"kind": "human", "text": phrased, "occurred_at": row["occurred_at"]}
        return {
            "kind": "human",
            "text": f"{actor} {verb} the ranking",
            "occurred_at": row["occurred_at"],
        }
    if kind == "placement":
        crew = payload.get("crew", "a crew")
        assets = len(payload.get("asset_ids", []))
        return {
            "kind": "human",
            "text": f"{actor} recorded {crew} placed against {assets} asset(s)",
            "occurred_at": row["occurred_at"],
        }
    if kind == "dismiss":
        return {
            "kind": "human",
            "text": f"{actor} dismissed a damage report as a false alarm",
            "occurred_at": row["occurred_at"],
        }
    return None


@router.get("/{scenario_id}/activity")
async def read_activity(request: Request, scenario_id: str):
    connection = request.app.state.db
    scenario = scenarios.find(connection, scenario_id)
    if scenario is None:
        return errors.error(404, "not_found", "That storm could not be found.")

    names = _actor_names(connection)
    entries: list[dict] = []

    # The storm arriving is a system event, in CHG-054's exact permitted shape.
    entries.append(
        {
            "kind": "system",
            "text": "Scenario loaded from 5 prepared files",
            "occurred_at": scenario["loaded_at"],
        }
    )

    for row in connection.execute(
        "select * from decision_records where scenario_id = ? order by seq desc limit ?",
        (scenario_id, FEED_LIMIT),
    ):
        entry = _decision_entry(row, names)
        if entry:
            entries.append(entry)

    for row in connection.execute(
        "select * from crew_staging where scenario_id = ? order by seq desc limit ?",
        (scenario_id, FEED_LIMIT),
    ):
        depots = len(json.loads(row["depots"]))
        entries.append(
            {
                "kind": "human",
                "text": (
                    f"{names.get(row['actor_user_id'], 'Somebody')} recorded a staging "
                    f"plan across {depots} depot(s)"
                ),
                "occurred_at": row["created_at"],
            }
        )

    for row in connection.execute(
        "select * from summaries where scenario_id = ? order by seq desc limit ?",
        (scenario_id, FEED_LIMIT),
    ):
        drafted_by = names.get(row["drafted_by"], "Somebody")
        entries.append(
            {
                "kind": "human",
                "text": f"{drafted_by} drafted a situation summary ({row['label']})",
                "occurred_at": row["drafted_at"],
            }
        )
        if row["approved_at"]:
            entries.append(
                {
                    "kind": "human",
                    "text": (
                        f"{names.get(row['approved_by'], 'Somebody')} approved the "
                        "situation summary"
                    ),
                    "occurred_at": row["approved_at"],
                }
            )

    # Access-control events from the queryable log (CHG-046). Global rather than
    # scenario-scoped — a sign-in is context for every storm on screen.
    for row in security.recent(connection, limit=10):
        entries.append(
            {"kind": "system", "text": row["detail"], "occurred_at": row["occurred_at"]}
        )

    entries.sort(key=lambda entry: entry["occurred_at"], reverse=True)
    return {"scenario_id": scenario_id, "items": entries[:FEED_LIMIT]}


@router.get("/{scenario_id}/movement")
async def read_movement(request: Request, scenario_id: str):
    """The stored diff behind "Since you last looked" (CHG-044).

    At revision 0 there is nothing to compare and the answer says so — `first_ranking`
    is a fact, not an apology, and the screen renders it in words rather than faking a
    delta the client's prompt forbids by name.
    """
    connection = request.app.state.db
    scenario = scenarios.find(connection, scenario_id)
    if scenario is None:
        return errors.error(404, "not_found", "That storm could not be found.")

    revision = scenario["forecast_revision"]
    rows = movement_store.for_revision(connection, scenario_id, revision)
    return {
        "scenario_id": scenario_id,
        "forecast_revision": revision,
        "first_ranking": revision == 0,
        "previous_label": rows[0]["previous_label"] if rows else None,
        "items": [views.movement_item(row) for row in rows],
        "moved_up_high": sum(1 for row in rows if row["band"] == "High"),
    }
