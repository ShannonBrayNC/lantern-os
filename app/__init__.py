"""Lantern OS application package and local SQLite compatibility migration."""

from __future__ import annotations

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "lantern.db"


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def _ensure_columns(
    connection: sqlite3.Connection,
    table: str,
    additions: dict[str, str],
) -> None:
    existing = _columns(connection, table)
    for column, definition in additions.items():
        if column not in existing:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def migrate_legacy_database() -> None:
    """Upgrade every prototype dashboard table without deleting local records."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        return

    with sqlite3.connect(DB_PATH) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS research (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT ''
            );
            """
        )

        _ensure_columns(
            connection,
            "tasks",
            {
                "workstream": "TEXT NOT NULL DEFAULT 'Operations'",
                "priority": "TEXT NOT NULL DEFAULT 'P1'",
                "revenue_impact": "TEXT NOT NULL DEFAULT 'Medium'",
                "due_date": "TEXT",
                "completed": "INTEGER NOT NULL DEFAULT 0",
            },
        )
        _ensure_columns(
            connection,
            "opportunities",
            {
                "account": "TEXT NOT NULL DEFAULT ''",
                "stage": "TEXT NOT NULL DEFAULT 'Prospecting'",
                "value": "REAL NOT NULL DEFAULT 0",
                "probability": "REAL NOT NULL DEFAULT 0",
            },
        )
        _ensure_columns(
            connection,
            "research",
            {
                "title": "TEXT NOT NULL DEFAULT ''",
                "progress": "INTEGER NOT NULL DEFAULT 0",
                "commercial_output": "TEXT NOT NULL DEFAULT ''",
            },
        )
        _ensure_columns(
            connection,
            "milestones",
            {
                "title": "TEXT NOT NULL DEFAULT ''",
                "target_date": "TEXT NOT NULL DEFAULT ''",
                "progress": "INTEGER NOT NULL DEFAULT 0",
            },
        )

        connection.commit()


migrate_legacy_database()
