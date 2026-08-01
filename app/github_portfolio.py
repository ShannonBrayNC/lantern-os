from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Any

import httpx

DEFAULT_REPOSITORIES = (
    "ShannonBrayNC/ETS",
    "Lantern-Protocol/SignalForge",
    "ShannonBrayNC/OpsHelm",
    "ShannonBrayNC/echocode-platform",
    "ShannonBrayNC/EchoMedia-ContentEngine",
    "ShannonBrayNC/christina-assistant",
)


@dataclass(frozen=True)
class RepositoryHealth:
    repository: str
    default_branch: str | None
    open_issues: int | None
    open_pull_requests: int | None
    latest_workflow: str
    latest_release: str | None
    health: str
    score: int
    refreshed_at: str
    stale: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GitHubPortfolioService:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client
        self._cache: dict[str, tuple[float, RepositoryHealth]] = {}
        self._lock = Lock()

    @staticmethod
    def repositories() -> list[str]:
        raw = os.getenv("LANTERN_GITHUB_REPOSITORIES", "")
        values = [item.strip() for item in raw.split(",") if item.strip()]
        return values or list(DEFAULT_REPOSITORIES)

    @staticmethod
    def ttl_seconds() -> int:
        try:
            return max(30, int(os.getenv("LANTERN_GITHUB_CACHE_SECONDS", "300")))
        except ValueError:
            return 300

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        token = os.getenv("LANTERN_GITHUB_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _http(self) -> httpx.Client:
        return self._client or httpx.Client(base_url="https://api.github.com", headers=self._headers(), timeout=8.0)

    def _get(self, client: httpx.Client, path: str, params: dict[str, Any] | None = None) -> Any:
        response = client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _score(workflow: str, open_prs: int, archived: bool) -> tuple[int, str]:
        score = 100
        if archived:
            score -= 60
        if workflow == "failure":
            score -= 45
        elif workflow in {"queued", "in_progress", "pending"}:
            score -= 10
        elif workflow in {"unknown", "none"}:
            score -= 15
        score -= min(open_prs * 3, 18)
        health = "healthy" if score >= 80 else "attention" if score >= 55 else "critical"
        return max(score, 0), health

    def fetch_repository(self, repository: str, force: bool = False) -> RepositoryHealth:
        now = time.time()
        with self._lock:
            cached = self._cache.get(repository)
        if cached and not force and now - cached[0] < self.ttl_seconds():
            return cached[1]

        timestamp = datetime.now(UTC).isoformat()
        try:
            client = self._http()
            repo = self._get(client, f"/repos/{repository}")
            pulls = self._get(client, f"/repos/{repository}/pulls", {"state": "open", "per_page": 100})
            runs_payload = self._get(client, f"/repos/{repository}/actions/runs", {"per_page": 1})
            releases = self._get(client, f"/repos/{repository}/releases", {"per_page": 1})
            runs = runs_payload.get("workflow_runs", []) if isinstance(runs_payload, dict) else []
            workflow = str((runs[0].get("conclusion") or runs[0].get("status")) if runs else "none")
            open_prs = len(pulls) if isinstance(pulls, list) else 0
            score, health = self._score(workflow, open_prs, bool(repo.get("archived")))
            result = RepositoryHealth(
                repository=repository,
                default_branch=repo.get("default_branch"),
                open_issues=max(int(repo.get("open_issues_count", 0)) - open_prs, 0),
                open_pull_requests=open_prs,
                latest_workflow=workflow,
                latest_release=(releases[0].get("tag_name") if isinstance(releases, list) and releases else None),
                health=health,
                score=score,
                refreshed_at=timestamp,
            )
            with self._lock:
                self._cache[repository] = (now, result)
            if self._client is None:
                client.close()
            return result
        except Exception as exc:  # connector failures are isolated per repository
            if cached:
                stale = RepositoryHealth(**{**cached[1].to_dict(), "stale": True, "error": str(exc), "refreshed_at": timestamp})
                return stale
            return RepositoryHealth(
                repository=repository,
                default_branch=None,
                open_issues=None,
                open_pull_requests=None,
                latest_workflow="unavailable",
                latest_release=None,
                health="unavailable",
                score=0,
                refreshed_at=timestamp,
                stale=False,
                error=str(exc),
            )

    def portfolio(self, force: bool = False) -> dict[str, Any]:
        repositories = [self.fetch_repository(name, force=force) for name in self.repositories()]
        available = [repo for repo in repositories if repo.health != "unavailable"]
        score = round(sum(repo.score for repo in available) / len(available)) if available else 0
        return {
            "score": score,
            "health": "healthy" if score >= 80 else "attention" if score >= 55 else "critical",
            "repository_count": len(repositories),
            "available_count": len(available),
            "repositories": [repo.to_dict() for repo in repositories],
            "refreshed_at": datetime.now(UTC).isoformat(),
        }


portfolio_service = GitHubPortfolioService()
