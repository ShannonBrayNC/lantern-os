from fastapi.testclient import TestClient

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
