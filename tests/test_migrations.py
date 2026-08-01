from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect


def test_alembic_baseline_creates_expected_schema(tmp_path: Path) -> None:
    database = tmp_path / "migration.db"
    url = f"sqlite:///{database.as_posix()}"
    env = {**os.environ, "LANTERN_DATABASE_URL": url}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
        env=env,
        capture_output=True,
        text=True,
    )
    inspector = inspect(create_engine(url))
    assert {
        "schema_meta",
        "tasks",
        "opportunities",
        "research",
        "milestones",
        "settings",
        "kpis",
    }.issubset(set(inspector.get_table_names()))
