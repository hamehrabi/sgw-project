"""TASK-001 acceptance criterion 7 — defined in `02-tasks/02-task-files/TASK-001.md`.

"The application fails at **startup**, with a named message, when a required configuration
value is missing."

Never at the first request during a storm, and never by quietly substituting a default.
ADR-006 is explicit that neither session limit has one: `.env.example` shipped them blank
with a startup failure "so that nobody could answer it by accident".
"""

import pytest
from conftest import TEST_ENV

REQUIRED = sorted(TEST_ENV) + ["DATABASE_PATH", "SCENARIO_UPLOAD_DIR"]


@pytest.mark.parametrize("missing", REQUIRED)
def test_startup_fails_when_a_required_value_is_absent(env, monkeypatch, missing):
    from app.config import ConfigError, load_config

    monkeypatch.delenv(missing, raising=False)

    with pytest.raises(ConfigError) as raised:
        load_config()

    # "with a named message" — a failure that does not say which value is missing sends
    # somebody to read the source at the moment the application will not start.
    assert missing in str(raised.value)


def test_the_application_itself_refuses_to_start(env, monkeypatch):
    from app.config import ConfigError
    from app.main import create_app

    monkeypatch.delenv("SESSION_IDLE_TIMEOUT_MINUTES", raising=False)

    with pytest.raises(ConfigError):
        create_app()


@pytest.mark.parametrize(
    "name,value",
    [
        ("SESSION_IDLE_TIMEOUT_MINUTES", "not-a-number"),
        ("SESSION_ABSOLUTE_MAX_HOURS", ""),
        ("PASSWORD_HASH_COST", "-1"),
        ("SESSION_IDLE_TIMEOUT_MINUTES", "0"),
    ],
)
def test_startup_fails_on_a_value_that_is_present_but_unusable(env, monkeypatch, name, value):
    from app.config import ConfigError, load_config

    monkeypatch.setenv(name, value)

    with pytest.raises(ConfigError) as raised:
        load_config()

    assert name in str(raised.value)


def test_a_complete_configuration_loads(env):
    from app.config import load_config

    config = load_config()

    assert config.session_idle_timeout_minutes == 240
    assert config.session_absolute_max_hours == 12


def test_no_secret_appears_in_the_failure_message(env, monkeypatch):
    """A startup error is written to a console and often into a deployment log."""
    from app.config import ConfigError, load_config

    monkeypatch.delenv("PASSWORD_HASH_COST", raising=False)

    with pytest.raises(ConfigError) as raised:
        load_config()

    assert TEST_ENV["SESSION_SIGNING_KEY"] not in str(raised.value)
