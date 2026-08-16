"""Configuration, read from the environment and validated once, at startup.

Two rules from the specification shape this module:

- **Nothing has a default.** ADR-006 shipped both session limits blank in `.env.example`
  "so that nobody could answer it by accident", and a default is exactly how an open
  question gets answered by accident.
- **A missing value fails at startup, named.** Never at the first request during a storm
  (TASK-001 step 2, acceptance criterion 7).

**The LLM guards are conditional on one required switch, and the switch has no default
either.** `LLM_ENABLED` must be set to exactly `true` or `false`: absence cannot be a
silent mode, and `false` is a decision somebody wrote down. When it is `true`, all five
guards ADR-009 makes mandatory (Q-029, Q-030) are required with it — a model with no cost
ceiling is an unbounded invoice, so half-configured is refused at startup rather than
discovered on one.
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
    # CHG-053: a temporary password's lifetime. A lifetime, so no default (ADR-006).
    temp_password_expiry_hours: int
    # The prepared dataset behind "Use sample storm data". It goes through the same parse
    # path as a real upload — this only says where the files are.
    sample_scenario_dir: str
    # CHG-040 / ADR-009. When false, the summary is assembled from figures and the model
    # is never called; the five guards below are then permitted to be absent.
    llm_enabled: bool
    openai_api_key: str | None
    openai_model: str | None
    llm_max_calls_per_ranking: int | None
    llm_monthly_cost_ceiling_usd: float | None
    llm_timeout_seconds: int | None

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


def _required_bool(env: Mapping[str, str], name: str) -> bool:
    raw = _required(env, name).lower()
    if raw not in ("true", "false"):
        # Exactly two spellings. "1", "yes" and "on" are how a typo becomes a mode.
        raise ConfigError(f"{name} must be exactly 'true' or 'false'.")
    return raw == "true"


def _required_float(env: Mapping[str, str], name: str, minimum: float, maximum: float) -> float:
    raw = _required(env, name)
    try:
        value = float(raw)
    except ValueError:
        raise ConfigError(f"{name} must be a number.") from None
    if not minimum <= value <= maximum:
        raise ConfigError(f"{name} must be between {minimum} and {maximum}.")
    return value


def load_config(env: Mapping[str, str] | None = None) -> Config:
    """Validate the whole environment and return it, or raise naming the first problem."""
    env = os.environ if env is None else env

    # The switch is read first because five other values hang off it. When the model is
    # off, its guards are not read at all — an invalid OPENAI_MODEL must not stop an
    # application that was never going to call one.
    llm_enabled = _required_bool(env, "LLM_ENABLED")

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
        # CHG-053. 24 is the shipped value; the number lives in the environment because it
        # is a lifetime, and ADR-006's rule for lifetimes is: read, never defaulted.
        temp_password_expiry_hours=_required_int(
            env, "TEMP_PASSWORD_EXPIRY_HOURS", minimum=1, maximum=168
        ),
        sample_scenario_dir=_required(env, "SAMPLE_SCENARIO_DIR"),
        llm_enabled=llm_enabled,
        # ADR-009 makes all five mandatory when the model is on (Q-029, Q-030). Absent and
        # unread when it is off: absence cannot be a silent mode either way.
        openai_api_key=_required(env, "OPENAI_API_KEY") if llm_enabled else None,
        openai_model=_required(env, "OPENAI_MODEL") if llm_enabled else None,
        llm_max_calls_per_ranking=(
            _required_int(env, "LLM_MAX_CALLS_PER_RANKING", minimum=1, maximum=100_000)
            if llm_enabled
            else None
        ),
        llm_monthly_cost_ceiling_usd=(
            _required_float(env, "LLM_MONTHLY_COST_CEILING_USD", minimum=0.01, maximum=100_000)
            if llm_enabled
            else None
        ),
        llm_timeout_seconds=(
            _required_int(env, "LLM_TIMEOUT_SECONDS", minimum=1, maximum=120)
            if llm_enabled
            else None
        ),
    )
