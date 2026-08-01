from fastapi.testclient import TestClient
from app.main import app


def test_health_reports_050():
    with TestClient(app) as client:
        response = client.get('/api/health')
        assert response.status_code == 200
        assert response.json()['version'] == '0.5.0'
        assert response.json()['schema'] == '0.5.0'


def test_dashboard_renders_operating_sections():
    with TestClient(app) as client:
        response = client.get('/')
        assert response.status_code == 200
        for marker in ('Mission Control', "Today's recommended moves", 'Operating KPIs', 'Research-to-revenue'):
            assert marker in response.text


def test_task_lifecycle():
    with TestClient(app) as client:
        created = client.post('/api/tasks', json={'title': '0.5 release validation'})
        assert created.status_code == 200
        task = created.json()
        assert client.patch(f"/api/tasks/{task['id']}/toggle").json()['completed'] is True
        assert client.delete(f"/api/tasks/{task['id']}").status_code == 204


def test_settings_and_kpis_are_persistent():
    with TestClient(app) as client:
        assert client.put('/api/settings/daily_focus', json={'value': 'Close the next design partner.'}).status_code == 200
        assert client.get('/api/settings').json()['daily_focus'] == 'Close the next design partner.'
        assert client.patch('/api/kpis/outreach', json={'actual': 12}).status_code == 200
        assert any(item['key'] == 'outreach' and item['actual'] == 12 for item in client.get('/api/kpis').json())


def test_recommendations_endpoint():
    with TestClient(app) as client:
        result = client.get('/api/recommendations')
        assert result.status_code == 200
        assert len(result.json()) >= 1
