"""Administrative commands, run on the host.

Accounts exist only through this command. "Roles are set in the database, not through any
endpoint. There is no self-service promotion path, at any version."
(`security-specification.md` §7)

    python -m app.cli create-user --name "Ops Manager" --email ops@sgw.example --role admin

The password is read from a prompt, never from an argument: an argument is in the shell
history and in the process list, which is a credential written down twice.
"""

import argparse
import getpass
import sqlite3
import sys

from app.config import ConfigError, load_config
from app.store import db, migrate, users

ROLES = ("admin", "user")


def read_password(prompt: str) -> str:
    """Prompt when there is a console; otherwise read a line from stdin.

    `getpass` on Windows reads the console device directly and ignores a pipe, so a
    provisioning script that fed it a password would hang rather than fail — which is the
    worst of the three outcomes. Neither branch echoes, and neither puts the value in an
    argument, where the shell history and the process list would both keep a copy.
    """
    if sys.stdin.isatty():
        return getpass.getpass(prompt)
    return sys.stdin.readline().rstrip("\n")


def create_user_command(arguments) -> int:
    config = load_config()
    connection = db.connect(config.database_path)
    migrate.run(connection)

    password = read_password("Password: ")
    if password != read_password("Repeat password: "):
        print("The two passwords do not match. No account was created.", file=sys.stderr)
        return 1
    if len(password) < 12:
        # Not a specified rule, and applied anyway: this is the only account system in
        # front of critical-infrastructure data, and there is no second factor (SEC-A-006).
        print("Use at least 12 characters. No account was created.", file=sys.stderr)
        return 1

    try:
        user_id = users.create_user(
            connection,
            name=arguments.name,
            email=arguments.email,
            password=password,
            role=arguments.role,
            cost=config.password_hash_cost,
        )
    except sqlite3.IntegrityError:
        # Either the address is taken or the role is not one of the two. Both are refused
        # by the database rather than by a check here (ADR-002).
        print("The database refused that account. Check the address and the role.", file=sys.stderr)
        return 1

    print(f"Created {user_id} with role {arguments.role}.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.cli", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create-user", help="Create an account.")
    create.add_argument("--name", required=True)
    create.add_argument("--email", required=True)
    create.add_argument("--role", required=True, choices=ROLES)
    create.set_defaults(handler=create_user_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        return arguments.handler(arguments)
    except ConfigError as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
