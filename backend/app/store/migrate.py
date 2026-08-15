"""Applying the raw-SQL migrations, in order, once each.

Schema first, then the code that depends on it (`database-design.md` §8).
"""

import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def applied(connection: sqlite3.Connection) -> set[str]:
    connection.execute(
        "create table if not exists schema_migrations ("
        " name text primary key, applied_at text not null)"
    )
    connection.commit()
    return {row["name"] for row in connection.execute("select name from schema_migrations")}


def pending(connection: sqlite3.Connection) -> list[Path]:
    done = applied(connection)
    return [path for path in sorted(MIGRATIONS_DIR.glob("*.up.sql")) if path.name not in done]


def run(connection: sqlite3.Connection) -> list[str]:
    """Apply every unapplied migration. Returns the names applied."""
    names = []
    for path in pending(connection):
        connection.executescript(path.read_text(encoding="utf-8"))
        connection.execute(
            "insert into schema_migrations (name, applied_at) values (?, datetime('now'))",
            (path.name,),
        )
        connection.commit()
        names.append(path.name)
    return names
