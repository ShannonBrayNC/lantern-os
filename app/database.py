from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_SQLITE_URL = f"sqlite:///{(DATA_DIR / 'lantern.db').as_posix()}"


def database_url() -> str:
    return os.getenv("LANTERN_DATABASE_URL", DEFAULT_SQLITE_URL)


def create_database_engine() -> Engine:
    url = database_url()
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


def normalize_legacy_data(target_engine: Engine) -> None:
    """Repair values accepted by legacy SQLite schemas but rejected by typed ORM columns.

    Older Lantern OS builds stored an empty string in ``tasks.created_at``. SQLAlchemy's
    DateTime processor correctly rejects that value before model instances can load.
    Normalize it before the first ORM query. The statement is safe and idempotent on
    both SQLite and PostgreSQL.
    """
    inspector = inspect(target_engine)
    if "tasks" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("tasks")}
    if "created_at" not in columns:
        return

    with target_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE tasks "
                "SET created_at = CURRENT_TIMESTAMP "
                "WHERE created_at IS NULL OR TRIM(CAST(created_at AS TEXT)) = ''"
            )
        )


engine = create_database_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
