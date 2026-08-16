"""The backend, seeded and served, for the browser tests.

End-to-end means both processes (ADR-008), so Playwright starts this alongside `next dev`.
Everything it writes goes under `.e2e/`, which is git-ignored and rebuilt on every run — a
browser suite that inherits yesterday's database passes for reasons nobody chose.

Accounts are created here because no endpoint creates one and none ever will
(`security-specification.md` §7). The passwords are fixtures, and the low hash cost is the
same configuration choice the pytest suite makes: 12 would add minutes and prove nothing.
"""

import os
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = ROOT / ".e2e"
PORT = 8100

E2E_PASSWORD = "e2e-fixture-password"

sys.path.insert(0, str(ROOT / "backend"))

shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True)

os.environ.update(
    APP_ENV="test",
    SESSION_SIGNING_KEY="e2e-signing-key-not-a-real-secret",
    SESSION_IDLE_TIMEOUT_MINUTES="240",
    SESSION_ABSOLUTE_MAX_HOURS="12",
    PASSWORD_HASH_COST="4",
    DATABASE_PATH=str(WORK / "app.db"),
    SCENARIO_UPLOAD_DIR=str(WORK / "scenarios"),
    SCENARIO_MAX_FILE_BYTES="8388608",
    SCENARIO_MAX_TOTAL_BYTES="10485760",
    SCENARIO_PARSE_TIMEOUT_SECONDS="120",
    SCENARIO_STALE_AFTER_HOURS="6",
    TEMP_PASSWORD_EXPIRY_HOURS="24",
    SAMPLE_SCENARIO_DIR=str(
        ROOT / "spec" / "03-tests" / "05-executable" / "fixtures" / "storm-with-seven-defects"
    ),
    LLM_ENABLED="false",
)

from app.config import load_config  # noqa: E402
from app.store import db, migrate, users  # noqa: E402

config = load_config()
connection = db.connect(config.database_path)
migrate.run(connection)
for name, email, role in (
    ("Ops Manager", "ops@sgw.example", "admin"),
    ("Dispatcher", "dispatch@sgw.example", "operator"),
):
    users.create_user(
        connection, name=name, email=email, password=E2E_PASSWORD, role=role, cost=4
    )
connection.close()

import uvicorn  # noqa: E402

uvicorn.run(
    "app.main:create_app", factory=True, host="127.0.0.1", port=PORT, log_level="warning"
)
