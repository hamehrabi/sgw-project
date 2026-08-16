"""Shared fixtures for the executable suite.

Tests come from acceptance criteria, not from the code that was just written
(`executable-tests.md`). Every fixture here exists to make a criterion in TASK-001 or a row
in `security-tests.md` checkable, and nothing here weakens one to make a test convenient.
"""

import pathlib

import pytest
from fastapi.testclient import TestClient

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def fixture_files(name: str = "storm-with-seven-defects") -> dict[str, bytes]:
    """A prepared scenario, as the upload endpoint would receive it.

    The shipped fixture carries all seven defects from `data-and-integration-spec.md` §4 on
    purpose, so the design is proven against dirty data rather than clean data.
    """
    return {path.name: path.read_bytes() for path in (FIXTURES / name).iterdir()}

# The four values TASK-001 reads. `PASSWORD_HASH_COST` is deliberately low here and only
# here: it is configuration, and a bcrypt cost of 12 would add minutes to the suite for no
# additional assurance. Every other value is the real one from `.env.example`, because
# ADR-006's two limits are what STEST-002 is testing.
TEST_ENV = {
    "APP_ENV": "test",
    "SESSION_SIGNING_KEY": "test-key-not-a-real-secret-and-never-a-default",
    "SESSION_IDLE_TIMEOUT_MINUTES": "240",
    "SESSION_ABSOLUTE_MAX_HOURS": "12",
    "PASSWORD_HASH_COST": "4",
    # Deliberately smaller than the shipped 8 MB / 10 MB, so the size refusals can be tested
    # without building an 8 MB fixture — and so a hard-coded limit would be caught, which is
    # the lesson AGENT.md's first row records.
    "SCENARIO_MAX_FILE_BYTES": "4096",
    "SCENARIO_MAX_TOTAL_BYTES": "16384",
    "SCENARIO_PARSE_TIMEOUT_SECONDS": "120",
    "SCENARIO_STALE_AFTER_HOURS": "6",
    # CHG-053: a temporary password's lifetime, read and never defaulted like ADR-006's two.
    "TEMP_PASSWORD_EXPIRY_HOURS": "24",
    # The sample-data button loads this through the same parse path as a real upload.
    "SAMPLE_SCENARIO_DIR": str(FIXTURES / "storm-with-seven-defects"),
    # Off in the suite: the tests that exercise the draft path monkeypatch the transport,
    # and nothing in this suite may reach outside the machine (CHG-040's verifier is pure
    # and is tested against strings).
    "LLM_ENABLED": "false",
}

ADMIN_PASSWORD = "correct-horse-battery-staple"
USER_PASSWORD = "another-entirely-different-one"


@pytest.fixture
def env(tmp_path, monkeypatch):
    """The configuration the application reads, with a database file per test."""
    for name, value in TEST_ENV.items():
        monkeypatch.setenv(name, value)
    db_path = tmp_path / "test.db"
    upload_dir = tmp_path / "scenarios"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("SCENARIO_UPLOAD_DIR", str(upload_dir))
    return {
        **TEST_ENV,
        "DATABASE_PATH": str(db_path),
        "SCENARIO_UPLOAD_DIR": str(upload_dir),
    }


@pytest.fixture
def application(env):
    from app.main import create_app

    return create_app()


@pytest.fixture
def client(application):
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def accounts(application):
    """One admin and one user.

    Created through the store, because no endpoint creates an account and none ever will:
    "Roles are set in the database, not through any endpoint. There is no self-service
    promotion path, at any version." (`security-specification.md` §7)
    """
    from app.store import users

    conn = application.state.db
    admin_id = users.create_user(
        conn, name="Ops Manager", email="admin@sgw.example", password=ADMIN_PASSWORD, role="admin"
    )
    user_id = users.create_user(
        conn, name="Dispatcher", email="user@sgw.example", password=USER_PASSWORD, role="operator"
    )
    return {
        "admin": {"id": admin_id, "email": "admin@sgw.example", "password": ADMIN_PASSWORD},
        "user": {"id": user_id, "email": "user@sgw.example", "password": USER_PASSWORD},
    }


def sign_in(client, email, password):
    return client.post("/api/v1/auth/session", json={"email": email, "password": password})


def build_application(monkeypatch, db_path, **overrides):
    """An application with a chosen configuration, on a chosen database file.

    Two review checks need this: proving a limit is read from configuration rather than
    hard-coded needs a value that is not the shipped one, and proving a session survives a
    restart needs a second application over the same file.
    """
    values = {
        **TEST_ENV,
        "DATABASE_PATH": str(db_path),
        "SCENARIO_UPLOAD_DIR": str(pathlib.Path(db_path).parent / "scenarios"),
        **overrides,
    }
    for name, value in values.items():
        monkeypatch.setenv(name, str(value))

    from app.main import create_app

    return create_app()
