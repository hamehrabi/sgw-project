"""Container entrypoint: prepare the data directory, optionally seed the first admin,
then hand the process to uvicorn.

**The bootstrap admin is the host operator's act, not an endpoint** — the same trust
level as the CLI (`security-specification.md` §7): it runs only from environment
variables the person launching the container set, and only while the users table is
EMPTY. Once any account exists, the variables are ignored; sign-up (CHG-061) covers
operators, and further admins come from `python -m app.cli create-user` inside the
container. Recorded as CHG-065.
"""

import os
import sys

sys.path.insert(0, "/app/backend")

from app.config import load_config  # noqa: E402
from app.store import db, migrate, users  # noqa: E402


def main() -> None:
    config = load_config()

    for path in (config.database_path, None):
        if path:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    os.makedirs(os.environ["SCENARIO_UPLOAD_DIR"], exist_ok=True)

    connection = db.connect(config.database_path)
    migrate.run(connection)

    email = (os.environ.get("BOOTSTRAP_ADMIN_EMAIL") or "").strip()
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD") or ""
    if email and password:
        existing = connection.execute("select count(*) from users").fetchone()[0]
        if existing:
            print(f"bootstrap: {existing} account(s) exist — bootstrap variables ignored")
        elif len(password) < 12:
            print(
                "bootstrap: BOOTSTRAP_ADMIN_PASSWORD is under 12 characters — refusing, "
                "the same bound the CLI and the password change enforce",
                file=sys.stderr,
            )
            raise SystemExit(1)
        else:
            users.create_user(
                connection,
                name=os.environ.get("BOOTSTRAP_ADMIN_NAME", "Administrator"),
                email=email,
                password=password,
                role="admin",
                cost=config.password_hash_cost,
            )
            print(f"bootstrap: admin account created for {email} — change its password")
    connection.close()

    os.execvp(
        "uvicorn",
        [
            "uvicorn",
            "app.main:create_app",
            "--factory",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ],
    )


if __name__ == "__main__":
    main()
