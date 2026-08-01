"""Lantern OS application package.

This module performs a small compatibility migration before ``app.main`` is
imported. Early Lantern OS prototypes used a narrower SQLite task schema. A
local database created by those builds can still be present when the current
application starts, because ``CREATE TABLE IF NOT EXISTS`` does not add newly
introduced columns. The dashboard then fails while reading those columns.

The migration is intentionally idempotent and preserves existing records.
Formal migrations will replace this bootstrap compatibility layer when the
application moves to Alembic/PostgreSQL.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "lantern.db"


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }


def migrate_legacy_database() -> None:
    """Bring databases from the prototype schema up to the current minimum."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        return

    with sqlite3.connect(DB_PATH) as connection:
        task_columns = _columns(connection, "tasks")
        if task_columns:
            additions = {
                "workstream": "TEXT NOT NULL DEFAULT 'Operations'",
                "priority": "TEXT NOT NULL DEFAULT 'P1'",
                "revenue_impact": "TEXT NOT NULL DEFAULT 'Medium'",
                "due_date": "TEXT",
                "completed": "INTEGER NOT NULL DEFAULT 0",
            }
            for column, definition in additions.items():
                if column not in task_columns:
                    connection.execute(
                        f"ALTER TABLE tasks ADD COLUMN {column} {definition}"
                    )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account TEXT NOT NULL,
                stage TEXT NOT NULL,
                value REAL NOT NULL,
                probability REAL NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS research (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                commercial_output TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                target_date TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        connection.commit()


migrate_legacy_database()
