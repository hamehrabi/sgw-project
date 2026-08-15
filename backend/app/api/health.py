"""The health check.

Public, and unthrottled on principle: it has to answer during an incident, and no traffic
level makes gating it correct (`runtime-and-scale.md` §1). It reports that the process is
up and its store is reachable, and nothing about the data inside.
"""

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
async def health(request: Request) -> dict:
    request.app.state.db.execute("select 1").fetchone()
    return {"status": "ok"}
