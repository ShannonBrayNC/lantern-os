from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.database import normalize_legacy_data
from app.models import Task


def test_empty_legacy_created_at_is_normalized(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE tasks ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "title VARCHAR(240) NOT NULL, "
                "workstream VARCHAR(100) NOT NULL DEFAULT 'Operations', "
                "priority VARCHAR(20) NOT NULL DEFAULT 'P1', "
                "revenue_impact VARCHAR(20) NOT NULL DEFAULT 'Medium', "
                "due_date VARCHAR(10), "
                "completed BOOLEAN NOT NULL DEFAULT 0, "
                "created_at DATETIME NOT NULL DEFAULT ''"
                ")"
            )
        )
        connection.execute(
            text(
                "INSERT INTO tasks "
                "(title, workstream, priority, revenue_impact, due_date, completed, created_at) "
                "VALUES ('Legacy task', 'Operations', 'P1', 'Medium', NULL, 0, '')"
            )
        )

    normalize_legacy_data(engine)

    with Session(engine) as session:
        task = session.get(Task, 1)
        assert task is not None
        assert task.title == "Legacy task"
        assert task.created_at is not None
