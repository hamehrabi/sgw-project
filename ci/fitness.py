"""The fitness-function gate.

A test proves the feature does what was asked. A fitness function proves the **system still
has the shape you decided on**. They are different jobs, they run as different stages, and
folding these into the test suite is how FF-002 decays while every feature test stays green
(`cicd-pipeline.md`, stage 4).

Wired here: **FF-001, FF-002, FF-004, FF-005, FF-006, FF-007** — six of the seven. FF-003 is
still `Not wired yet` and prints its own line every run rather than being silently absent.

**FF-004 issues a real UPDATE and a real DELETE and requires both to be refused.** Inspecting
the schema for two trigger names is not the same check: a trigger can be present and wrong.

    python ci/fitness.py        # exit 0 = the shape held; exit 1 = block the merge
"""

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend" / "app"
FRONTEND = ROOT / "frontend"

MODULES = ("api", "scoring", "loader", "store")

# ADR-007's numbers. None of them may appear in the frontend: the scoring module is never
# "reimplemented, mirrored, or partially duplicated in the frontend for display purposes"
# (ADR-008). Weights, band boundaries, and the reason-strength thresholds.
SCORING_CONSTANTS = ("0.40", "0.25", "0.20", "0.15", ">= 60", ">= 30")


def imports_of(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
        elif isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
    return found


def module_graph() -> dict[str, set[str]]:
    graph = {name: set() for name in MODULES}
    for name in MODULES:
        for path in (BACKEND / name).rglob("*.py"):
            for imported in imports_of(path):
                for other in MODULES:
                    if imported.startswith(f"app.{other}") and other != name:
                        graph[name].add(other)
    return graph


def ff_001_no_import_cycle() -> list[str]:
    """No import cycle between the scoring module, the API layer, and the data layer."""
    graph = module_graph()
    cycles = []

    def walk(node, seen):
        for nxt in sorted(graph[node]):
            if nxt in seen:
                cycles.append(" -> ".join([*seen, nxt]))
            else:
                walk(nxt, [*seen, nxt])

    for start in MODULES:
        walk(start, [start])
    return [f"FF-001 import cycle: {c}" for c in sorted(set(cycles))]


def ff_002_scoring_stays_behind_the_api() -> list[str]:
    """(a) `scoring` is imported by `api` and nothing else. (b) no scoring constant in the
    frontend. Restated by CHG-010 — the old form could not fail under ADR-008."""
    failures = []
    graph = module_graph()
    for name in ("store", "loader"):
        if "scoring" in graph[name]:
            failures.append(f"FF-002(a) `{name}` imports `scoring`; only `api` may")

    if FRONTEND.exists():
        sources = [
            p
            for suffix in ("*.ts", "*.tsx")
            for p in FRONTEND.rglob(suffix)
            if "node_modules" not in p.parts and ".next" not in p.parts
        ]
        for path in sources:
            text = path.read_text(encoding="utf-8")
            for constant in SCORING_CONSTANTS:
                if constant in text:
                    rel = path.relative_to(ROOT)
                    failures.append(f"FF-002(b) scoring constant {constant!r} in {rel}")
    return failures


def ff_006_seven_defects_caught() -> list[str]:
    """Each of the seven known defects is caught by its own check, against a fixture that
    deliberately contains all seven. Threshold: 7 of 7."""
    sys.path.insert(0, str(ROOT / "backend"))
    fixture = ROOT / "spec" / "03-tests" / "05-executable" / "fixtures" / "storm-with-seven-defects"
    if not fixture.is_dir():
        return ["FF-006 the seven-defect fixture is missing"]

    from app.loader.load import load_scenario

    result = load_scenario({p.name: p.read_bytes() for p in fixture.iterdir()})
    caught = {finding.defect for finding in result.findings}
    missing = sorted({1, 2, 3, 4, 5, 6, 7} - caught)
    if not missing:
        return []
    return [f"FF-006 caught {len(caught)} of 7; no check fired for defect(s) {missing}"]


def ff_007_no_reason_outruns_its_arithmetic() -> list[str]:
    """No displayed reason names a factor absent from its computed input, or asserts a
    strength the arithmetic did not produce (ADR-009 rule 3).

    **Today this guards the computed text; when a model phrases it, the same check guards the
    model.** That is the point of wiring it now rather than with the phrasing layer: the rule
    is "output is validated against its input before display", and the validation should exist
    before there is anything untrusted to validate.
    """
    sys.path.insert(0, str(ROOT / "backend"))
    fixture = ROOT / "spec" / "03-tests" / "05-executable" / "fixtures" / "storm-with-seven-defects"

    from app.loader.load import load_scenario
    from app.scoring import references
    from app.scoring.rank import rank_assets

    result = load_scenario({p.name: p.read_bytes() for p in fixture.iterdir()})
    failures = []
    for item in rank_assets(result.assets):
        if item.score is None:
            if item.reasons:
                failures.append(f"FF-007 {item.external_ids} is unscored and carries reasons")
            continue
        for reason in item.reasons:
            if reason.factor not in references.WEIGHTS:
                failures.append(f"FF-007 reason names unknown factor {reason.factor!r}")
            share = reason.contribution / item.score
            expected = (
                "Strong"
                if share >= references.STRENGTH_STRONG_AT
                else "Moderate"
                if share >= references.STRENGTH_MODERATE_AT
                else "Slight"
            )
            if reason.strength != expected:
                failures.append(
                    f"FF-007 {reason.factor} contributed {share:.0%} and claims "
                    f"{reason.strength}, not {expected}"
                )
    return failures


def _loaded_and_ranked(tmp):
    """A live application with one storm loaded and its ranking delivered."""
    import os

    os.environ.update(
        APP_ENV="test", SESSION_SIGNING_KEY="fitness-gate-key", SESSION_IDLE_TIMEOUT_MINUTES="240",
        SESSION_ABSOLUTE_MAX_HOURS="12", PASSWORD_HASH_COST="4",
        DATABASE_PATH=str(tmp / "gate.db"), SCENARIO_UPLOAD_DIR=str(tmp / "scenarios"),
        SCENARIO_MAX_FILE_BYTES="8388608", SCENARIO_MAX_TOTAL_BYTES="10485760",
        SCENARIO_PARSE_TIMEOUT_SECONDS="120", SCENARIO_STALE_AFTER_HOURS="6",
    )
    from app.main import create_app
    from app.store import users
    from fastapi.testclient import TestClient

    fixture = ROOT / "spec" / "03-tests" / "05-executable" / "fixtures" / "storm-with-seven-defects"
    app = create_app()
    users.create_user(
        app.state.db, name="Gate", email="gate@sgw.example", password="gate-password", role="admin"
    )
    client = TestClient(app)
    client.post("/api/v1/auth/session", json={"email": "gate@sgw.example",
                                              "password": "gate-password"})
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "gate", "source_note": "gate"},
        files=[("files", (p.name, p.read_bytes(), "text/csv")) for p in fixture.iterdir()],
    )
    scenario_id = created.json()["scenario_id"]
    ranking = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    return app, scenario_id, ranking


def ff_004_decision_record_is_append_only() -> list[str]:
    """Both triggers exist, **and** an UPDATE issued against the table is refused by the
    database (ADR-004).

    Checking the schema is not enough and the register says so: a trigger can be present and
    disabled, or present and wrong. The only proof is to issue the statement and require the
    refusal.
    """
    import sqlite3
    import tempfile
    from pathlib import Path as _Path

    failures = []
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        app, _, _ = _loaded_and_ranked(_Path(tmpdir))
        connection = app.state.db
        triggers = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type = 'trigger'"
            )
        }
        for name in ("decision_records_no_update", "decision_records_no_delete"):
            if name not in triggers:
                failures.append(f"FF-004 trigger {name} is absent")

        row = connection.execute("select * from decision_records limit 1").fetchone()
        if row is None:
            return [*failures, "FF-004 no decision_records row exists to attempt an UPDATE on"]

        for statement, params in (
            ("update decision_records set payload = '{}' where id = ?", (row["id"],)),
            ("delete from decision_records where id = ?", (row["id"],)),
        ):
            try:
                connection.execute(statement, params)
                connection.commit()
                failures.append(f"FF-004 the database ACCEPTED: {statement.split(' where')[0]}")
            except sqlite3.IntegrityError:
                pass
        connection.close()
    return failures


def ff_005_every_ranking_is_recorded() -> list[str]:
    """Every delivered ranking has a matching `decision_records` row of kind
    `recommendation`, so what was shown can be reconstructed later (REQ-F-009)."""
    import tempfile
    from pathlib import Path as _Path

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        app, scenario_id, ranking = _loaded_and_ranked(_Path(tmpdir))
        rows = app.state.db.execute(
            "select * from decision_records where kind = 'recommendation'"
        ).fetchall()
        failures = []
        if len(rows) != 1:
            failures.append(f"FF-005 {len(rows)} recommendation rows for one delivered ranking")
        elif rows[0]["id"] != ranking.get("recommendation_id"):
            failures.append("FF-005 the delivered ranking does not name its recorded row")
        app.state.db.close()
    return failures


NOT_WIRED = {
    "FF-003": "needs a file-reading render path to guard — no view has one (CHG-013)",
}


def main() -> int:
    failures = ff_001_no_import_cycle() + ff_002_scoring_stays_behind_the_api()
    failures += ff_006_seven_defects_caught() + ff_007_no_reason_outruns_its_arithmetic()
    failures += ff_004_decision_record_is_append_only() + ff_005_every_ranking_is_recorded()

    for name, reason in NOT_WIRED.items():
        print(f"  {name}  NOT WIRED - {reason}")

    if failures:
        print("\nFITNESS GATE FAILED")
        for failure in failures:
            print(f"  {failure}")
        return 1

    print("\n  FF-001  ok - no import cycle")
    print("  FF-002  ok - scoring stays behind the API; no scoring constant in the frontend")
    print("  FF-004  ok - both triggers present, and the database refused a real UPDATE")
    print("  FF-005  ok - the delivered ranking names its recorded recommendation")
    print("  FF-006  ok - 7 of 7 defects caught by their own check")
    print("  FF-007  ok - every reason names a real factor and claims the strength it earned")
    print("\nFITNESS GATE PASSED (6 of 7 wired)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
