import os

from fastapi.testclient import TestClient

os.environ.setdefault("LANTERN_AUTH_MODE", "local")
os.environ.setdefault("LANTERN_LOCAL_ROLE", "Owner")

from app.main import app


def test_health_reports_auth_mode():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["version"] == "0.6.0"
        assert response.json()["schema"] == "0.6.0"
        assert response.json()["auth_mode"] == "local"


def test_dashboard_renders_authenticated_identity():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        for marker in ("Mission Control", "Today's recommended moves", "Operating KPIs", "Research-to-revenue", "Lantern Owner · Owner"):
            assert marker in response.text


def test_current_principal_endpoint():
    with TestClient(app) as client:
        principal = client.get("/api/me")
        assert principal.status_code == 200
        assert principal.json()["role"] == "Owner"
        assert principal.json()["source"] == "local"


def test_task_lifecycle():
    with TestClient(app) as client:
        created = client.post("/api/tasks", json={"title": "authentication sprint validation"})
        assert created.status_code == 200
        task = created.json()
        assert client.patch(f"/api/tasks/{task['id']}/toggle").json()["completed"] is True
        assert client.delete(f"/api/tasks/{task['id']}").status_code == 204


def test_viewer_cannot_mutate(monkeypatch):
    monkeypatch.setenv("LANTERN_LOCAL_ROLE", "Viewer")
    with TestClient(app) as client:
        assert client.get("/api/tasks").status_code == 200
        denied = client.post("/api/tasks", json={"title": "should not be created"})
        assert denied.status_code == 403
        assert client.put("/api/settings/daily_focus", json={"value": "Denied"}).status_code == 403
    monkeypatch.setenv("LANTERN_LOCAL_ROLE", "Owner")


def test_operator_can_update_kpi_but_not_settings(monkeypatch):
    monkeypatch.setenv("LANTERN_LOCAL_ROLE", "Operator")
    with TestClient(app) as client:
        assert client.patch("/api/kpis/outreach", json={"actual": 12}).status_code == 200
        assert client.put("/api/settings/daily_focus", json={"value": "Denied"}).status_code == 403
    monkeypatch.setenv("LANTERN_LOCAL_ROLE", "Owner")


def test_recommendations_endpoint():
    with TestClient(app) as client:
        result = client.get("/api/recommendations")
        assert result.status_code == 200
        assert len(result.json()) >= 1
