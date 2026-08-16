"""Stage 7 of `07-ops/01-deployment/cicd-pipeline.md` — the trigger check.

**Run after migrate and before deploy, and it is not a schema inspection.** BR-004's only
enforcement is two triggers (ADR-004); a migration can drop one; nothing else in the pipeline
would notice. So this stage applies **every migration to an empty database**, writes one real
`decision_records` row, and then issues a real `UPDATE` and a real `DELETE` against it and
requires the database to refuse both.

**Why this is a separate stage from FF-004 rather than the same check twice.** FF-004 (stage 4)
proves the guarantee holds on a database the *application* built — load, rank, deliver — so it
answers *is the running system append-only*. This stage answers the different question
`cicd-pipeline.md` asks at stage 7: *did the migration that just ran leave the guarantee
standing*. It boots no application and touches no route; its only input is
`store/migrate.py::run`. A migration whose last statement drops a trigger is caught here without
anything else in the system having to work first.

**The haystack is asserted before the needles.** `AGENT.md`'s standing rule — *any walk of a
framework's own structures starts by naming one thing it must find* — applies literally to a
query over `sqlite_master`: reporting *both triggers are present* against an enumeration that
returned nothing is the failure this repository has now recorded three times. Two triggers this
stage is not about must be in the same result before the two it is about are believed, and the
`UPDATE` must be refused **by its own sentence**, not merely by an exception class, because
`decision_records` carries other constraints that raise the same class.
"""

import sqlite3
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

from app.store import db, migrate  # noqa: E402

APPEND_ONLY = ("decision_records_no_update", "decision_records_no_delete")

# Two triggers this stage is NOT about. If a walk of `sqlite_master` cannot find these, it has
# not found the schema, and its silence about the two above means nothing.
HAYSTACK = ("scenarios_identity_shape", "risk_scores_no_update")

REFUSAL = "decision_records is append-only"

DIGEST = "a" * 64


def _seed(connection: sqlite3.Connection) -> str:
    """One user, one storm, one actorless `recommendation` row — the smallest real subject."""
    connection.execute(
        "insert into users (id, name, email, password_hash, role, created_at)"
        " values ('u-gate', 'Gate', 'gate@sgw.example', 'x', 'admin', '2026-01-01T00:00:00Z')"
    )
    connection.execute(
        "insert into scenarios (id, name, source_note, loaded_by, loaded_at,"
        " forecast_revision, content_key)"
        " values ('s-gate', 'Gate storm', 'stage 7', 'u-gate', '2026-01-01T00:00:00Z', 0, ?)",
        (DIGEST,),
    )
    connection.execute(
        "insert into decision_records (id, scenario_id, occurred_at, actor_user_id, kind,"
        " subject_type, subject_id, payload)"
        " values ('d-gate', 's-gate', '2026-01-01T00:00:00Z', null, 'recommendation',"
        " 'ranking', 's-gate:0', '{\"forecast_revision\": 0}')"
    )
    connection.commit()
    return "d-gate"


def check() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        connection = db.connect(str(Path(tmpdir) / "gate.db"))
        try:
            applied = migrate.run(connection)
            if not applied:
                return ["stage 7: no migration ran, so there is nothing to check the schema of"]

            triggers = {
                row[0]
                for row in connection.execute(
                    "select name from sqlite_master where type = 'trigger'"
                )
            }
            for name in HAYSTACK:
                if name not in triggers:
                    failures.append(
                        f"stage 7: the trigger walk did not find {name}, so it has not found the"
                        " schema and its silence about the append-only pair proves nothing"
                    )
            if failures:
                return failures

            for name in APPEND_ONLY:
                if name not in triggers:
                    failures.append(f"stage 7: trigger {name} is absent after migrate")
            if failures:
                return failures

            record_id = _seed(connection)
            before = dict(
                connection.execute(
                    "select * from decision_records where id = ?", (record_id,)
                ).fetchone()
            )

            for label, statement in (
                ("UPDATE", "update decision_records set payload = '{}' where id = ?"),
                ("DELETE", "delete from decision_records where id = ?"),
            ):
                try:
                    connection.execute(statement, (record_id,))
                    connection.commit()
                except sqlite3.Error as refusal:
                    if REFUSAL not in str(refusal):
                        failures.append(
                            f"stage 7: the {label} was refused, but for another rule than BR-004"
                            f" — {refusal}"
                        )
                else:
                    failures.append(f"stage 7: the database ACCEPTED a real {label} (BR-004)")

            after = connection.execute(
                "select * from decision_records where id = ?", (record_id,)
            ).fetchone()
            if after is None:
                failures.append("stage 7: the record is gone after a refused DELETE")
            elif dict(after) != before:
                failures.append("stage 7: the record moved after a refused UPDATE")
        finally:
            connection.close()
    return failures


def main() -> int:
    failures = check()
    if failures:
        print("TRIGGER GATE FAILED")
        for failure in failures:
            print(f"  {failure}")
        return 1
    print("  BR-004  ok - after migrate, a real UPDATE and a real DELETE were both refused")
    print("TRIGGER GATE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
