"""Lantern OS application package with legacy SQLite compatibility."""
from __future__ import annotations
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "lantern.db"


def columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}


def migrate_table(connection: sqlite3.Connection, table: str, additions: dict[str, str]) -> None:
    existing = columns(connection, table)
    for column, definition in additions.items():
        if existing and column not in existing:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def migrate_legacy_database() -> None:
    if not DB_PATH.exists():
        return
    with sqlite3.connect(DB_PATH) as connection:
        migrate_table(connection, "tasks", {"workstream":"TEXT NOT NULL DEFAULT 'Operations'","priority":"TEXT NOT NULL DEFAULT 'P1'","revenue_impact":"TEXT NOT NULL DEFAULT 'Medium'","due_date":"TEXT","completed":"INTEGER NOT NULL DEFAULT 0","created_at":"TEXT NOT NULL DEFAULT ''"})
        migrate_table(connection, "opportunities", {"account":"TEXT NOT NULL DEFAULT ''","stage":"TEXT NOT NULL DEFAULT 'Prospecting'","value":"REAL NOT NULL DEFAULT 0","probability":"REAL NOT NULL DEFAULT 0","next_action":"TEXT NOT NULL DEFAULT ''","next_date":"TEXT"})
        migrate_table(connection, "research", {"title":"TEXT NOT NULL DEFAULT ''","progress":"INTEGER NOT NULL DEFAULT 0","commercial_output":"TEXT NOT NULL DEFAULT ''","next_action":"TEXT NOT NULL DEFAULT ''"})
        migrate_table(connection, "milestones", {"title":"TEXT NOT NULL DEFAULT ''","target_date":"TEXT NOT NULL DEFAULT ''","progress":"INTEGER NOT NULL DEFAULT 0","owner":"TEXT NOT NULL DEFAULT 'Founder'"})
        connection.commit()

migrate_legacy_database()
