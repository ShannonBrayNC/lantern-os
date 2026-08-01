import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

import app as app_package
from app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_dashboard_renders() -> None:
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "Mission Control" in response.text
        assert "Daily execution" in response.text


def test_task_lifecycle() -> None:
    with TestClient(app) as client:
        created = client.post("/api/tasks", json={"title": "Connector validation task"})
        assert created.status_code == 200
        task = created.json()
        toggled = client.patch(f"/api/tasks/{task['id']}/toggle")
        assert toggled.status_code == 200
        assert toggled.json()["completed"] is True
        assert client.delete(f"/api/tasks/{task['id']}").status_code == 204


def test_legacy_database_is_upgraded_without_data_loss(
    tmp_path: Path, monkeypatch
) -> None:
    database = tmp_path / "lantern.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL
            )
            """
        )
        connection.execute("INSERT INTO tasks(title) VALUES(?)", ("Legacy task",))
        connection.commit()

    monkeypatch.setattr(app_package, "DATA_DIR", tmp_path)
    monkeypatch.setattr(app_package, "DB_PATH", database)
    app_package.migrate_legacy_database()

    with sqlite3.connect(database) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(tasks)").fetchall()
        }
        title = connection.execute("SELECT title FROM tasks").fetchone()[0]

    assert {
        "workstream",
        "priority",
        "revenue_impact",
        "due_date",
        "completed",
    }.issubset(columns)
    assert title == "Legacy task"
