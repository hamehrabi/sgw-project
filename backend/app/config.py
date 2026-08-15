"""Configuration, read from the environment and validated once, at startup.

Two rules from the specification shape this module:

- **Nothing has a default.** ADR-006 shipped both session limits blank in `.env.example`
  "so that nobody could answer it by accident", and a default is exactly how an open
  question gets answered by accident.
- **A missing value fails at startup, named.** Never at the first request during a storm
  (TASK-001 step 2, acceptance criterion 7).

Only the values TASK-001 actually reads are required here. The scenario limits and the
LLM guards are deliberately absent: requiring them now would block this task on Q-029 and
Q-030, which `task-index.md` is explicit do not block building.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Raised at startup when configuration is missing or unusable."""


@dataclass(frozen=True)
class Config:
    app_env: str
    session_signing_key: str
    session_idle_timeout_minutes: int
    session_absolute_max_hours: int
    password_hash_cost: int
    database_path: str
    scenario_upload_dir: str
    scenario_max_file_bytes: int
    scenario_max_total_bytes: int
    scenario_parse_timeout_seconds: int
    scenario_stale_after_hours: int

    @property
    def cookies_require_https(self) -> bool:
        return self.app_env not in ("development", "test")


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise ConfigError(
            f"{name} is not set. It has no default: set it in the environment before starting."
        )
    return value


def _required_int(env: Mapping[str, str], name: str, minimum: int, maximum: int) -> int:
    raw = _required(env, name)
    try:
        value = int(raw)
    except ValueError:
        # The value is never echoed — a configuration error is written to consoles and
        # deployment logs, and one of these variables is a signing key.
        raise ConfigError(f"{name} must be a whole number.") from None
    if not minimum <= value <= maximum:
        raise ConfigError(f"{name} must be between {minimum} and {maximum}.")
    return value


def load_config(env: Mapping[str, str] | None = None) -> Config:
    """Validate the whole environment and return it, or raise naming the first problem."""
    env = os.environ if env is None else env

    return Config(
        app_env=_required(env, "APP_ENV"),
        session_signing_key=_required(env, "SESSION_SIGNING_KEY"),
        # ADR-006: 240 minutes idle, 12 hours absolute. Read, never hard-coded.
        session_idle_timeout_minutes=_required_int(
            env, "SESSION_IDLE_TIMEOUT_MINUTES", minimum=1, maximum=60 * 24
        ),
        session_absolute_max_hours=_required_int(
            env, "SESSION_ABSOLUTE_MAX_HOURS", minimum=1, maximum=24 * 7
        ),
        # bcrypt's own range. 12 is the shipped value; the suite lowers it, which is what
        # configuration is for.
        password_hash_cost=_required_int(env, "PASSWORD_HASH_COST", minimum=4, maximum=31),
        database_path=_required(env, "DATABASE_PATH"),
        # Q-017: a prepared scenario is a manifest plus four CSVs, under 5 MB at demo scale.
        # The shipped limits sit at roughly double, so a legitimate dataset never trips them
        # and an unbounded upload cannot pass.
        scenario_upload_dir=_required(env, "SCENARIO_UPLOAD_DIR"),
        scenario_max_file_bytes=_required_int(
            env, "SCENARIO_MAX_FILE_BYTES", minimum=1, maximum=1_073_741_824
        ),
        scenario_max_total_bytes=_required_int(
            env, "SCENARIO_MAX_TOTAL_BYTES", minimum=1, maximum=1_073_741_824
        ),
        scenario_parse_timeout_seconds=_required_int(
            env, "SCENARIO_PARSE_TIMEOUT_SECONDS", minimum=1, maximum=3600
        ),
        # CHG-013. 6, from the National Hurricane Center's 6-hourly full advisories: older
        # than that and a newer forecast almost certainly exists and is not on screen. No
        # default, like ADR-006's two — the reasoning belongs in the change log, not in a
        # constant somebody can quietly adjust.
        scenario_stale_after_hours=_required_int(
            env, "SCENARIO_STALE_AFTER_HOURS", minimum=1, maximum=168
        ),
    )
