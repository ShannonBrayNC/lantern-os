import httpx

from app.github_portfolio import GitHubPortfolioService


def mock_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/pulls"):
        return httpx.Response(200, json=[{"number": 1}])
    if path.endswith("/actions/runs"):
        return httpx.Response(
            200,
            json={
                "workflow_runs": [
                    {"status": "completed", "conclusion": "success"}
                ]
            },
        )
    if path.endswith("/releases"):
        return httpx.Response(200, json=[{"tag_name": "v0.8.0"}])
    if path.endswith("/broken"):
        return httpx.Response(500, json={"message": "failure"})
    return httpx.Response(
        200,
        json={"default_branch": "main", "open_issues_count": 4, "archived": False},
    )


def test_portfolio_uses_mocked_github_responses(monkeypatch):
    monkeypatch.setenv("LANTERN_GITHUB_REPOSITORIES", "example/healthy")
    client = httpx.Client(
        transport=httpx.MockTransport(mock_handler),
        base_url="https://api.github.test",
    )
    service = GitHubPortfolioService(client=client)
    result = service.portfolio()
    repo = result["repositories"][0]
    assert result["available_count"] == 1
    assert repo["default_branch"] == "main"
    assert repo["open_pull_requests"] == 1
    assert repo["open_issues"] == 3
    assert repo["latest_workflow"] == "success"
    assert repo["latest_release"] == "v0.8.0"
    assert repo["health"] == "healthy"


def test_connector_failure_is_isolated(monkeypatch):
    monkeypatch.setenv("LANTERN_GITHUB_REPOSITORIES", "example/broken")

    def failing_handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"message": "offline"})

    client = httpx.Client(
        transport=httpx.MockTransport(failing_handler),
        base_url="https://api.github.test",
    )
    service = GitHubPortfolioService(client=client)
    result = service.portfolio()
    assert result["repository_count"] == 1
    assert result["available_count"] == 0
    assert result["repositories"][0]["health"] == "unavailable"
    assert result["repositories"][0]["error"]


def test_disabled_connector_does_not_make_network_calls(monkeypatch):
    monkeypatch.setenv("LANTERN_GITHUB_ENABLED", "false")
    monkeypatch.setenv("LANTERN_GITHUB_REPOSITORIES", "example/disabled")
    service = GitHubPortfolioService()
    result = service.portfolio()
    assert result["enabled"] is False
    assert result["repositories"][0]["error"] == "GitHub integration is disabled"
