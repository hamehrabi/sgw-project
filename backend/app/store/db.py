"""The connection to the single embedded database file (ADR-002)."""

import sqlite3
from pathlib import Path


def connect(database_path: str) -> sqlite3.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    # Off by default in SQLite, which would make every `references` clause in the schema
    # decorative. ADR-002 puts constraints in the store; this is what makes them real.
    connection.execute("pragma foreign_keys = on")
    connection.execute("pragma journal_mode = wal")
    return connection
