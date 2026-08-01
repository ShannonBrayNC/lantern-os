from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

EXPECTED_TABLES = {
    "schema_meta",
    "tasks",
    "opportunities",
    "research",
    "milestones",
    "settings",
    "kpis",
}


def run_upgrade(url: str) -> None:
    env = {**os.environ, "LANTERN_DATABASE_URL": url}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
        env=env,
        capture_output=True,
        text=True,
    )


def test_alembic_baseline_creates_expected_schema(tmp_path: Path) -> None:
    database = tmp_path / "migration.db"
    url = f"sqlite:///{database.as_posix()}"

    run_upgrade(url)

    inspector = inspect(create_engine(url))
    assert EXPECTED_TABLES.issubset(set(inspector.get_table_names()))
    assert "alembic_version" in inspector.get_table_names()


def test_alembic_baseline_adopts_existing_schema(tmp_path: Path) -> None:
    database = tmp_path / "legacy.db"
    url = f"sqlite:///{database.as_posix()}"
    engine = create_engine(url)

    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE schema_meta "
                '("key" VARCHAR(100) PRIMARY KEY, value VARCHAR(100) NOT NULL)'
            )
        )
        connection.execute(
            text("INSERT INTO schema_meta (\"key\", value) VALUES ('version', '0.8.0')")
        )

    run_upgrade(url)

    inspector = inspect(engine)
    assert EXPECTED_TABLES.issubset(set(inspector.get_table_names()))
    assert "alembic_version" in inspector.get_table_names()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT value FROM schema_meta")).scalar_one() == "0.8.0"
