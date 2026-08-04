from __future__ import annotations

import asyncio

import pytest

from lantern_runtime import (
    DependencyCycleError,
    DuplicateServiceError,
    HealthReport,
    HealthStatus,
    LifecycleState,
    MissingDependencyError,
    RuntimeCoordinator,
    ServiceDescriptor,
    ServiceRegistry,
)


class FakeService:
    def __init__(
        self,
        name: str,
        *,
        dependencies: tuple[str, ...] = (),
        priority: int = 100,
        health_status: HealthStatus = HealthStatus.HEALTHY,
        fail_start: bool = False,
        calls: list[str] | None = None,
    ) -> None:
        self.descriptor = ServiceDescriptor(
            name=name,
            version="1.0.0",
            dependencies=dependencies,
            startup_priority=priority,
        )
        self.health_status = health_status
        self.fail_start = fail_start
        self.calls = calls if calls is not None else []

    async def start(self) -> None:
        self.calls.append(f"start:{self.descriptor.name}")
        if self.fail_start:
            raise RuntimeError("start failed")

    async def stop(self) -> None:
        self.calls.append(f"stop:{self.descriptor.name}")

    async def health(self) -> HealthReport:
        return HealthReport(service=self.descriptor.name, status=self.health_status)


def test_registry_rejects_duplicate_names() -> None:
    registry = ServiceRegistry()
    registry.register(FakeService("alpha"))
    with pytest.raises(DuplicateServiceError):
        registry.register(FakeService("alpha"))


def test_registry_rejects_missing_dependencies() -> None:
    registry = ServiceRegistry()
    registry.register(FakeService("consumer", dependencies=("provider",)))
    with pytest.raises(MissingDependencyError):
        registry.startup_order()


def test_registry_rejects_dependency_cycles() -> None:
    registry = ServiceRegistry()
    registry.register(FakeService("alpha", dependencies=("beta",)))
    registry.register(FakeService("beta", dependencies=("alpha",)))
    with pytest.raises(DependencyCycleError):
        registry.startup_order()


def test_startup_respects_dependencies_and_shutdown_reverses_order() -> None:
    calls: list[str] = []
    registry = ServiceRegistry()
    registry.register(FakeService("portal", dependencies=("evidence",), calls=calls))
    registry.register(FakeService("identity", priority=10, calls=calls))
    registry.register(
        FakeService("evidence", dependencies=("identity",), priority=20, calls=calls)
    )
    runtime = RuntimeCoordinator(registry)

    asyncio.run(runtime.start())
    assert calls == ["start:identity", "start:evidence", "start:portal"]
    assert runtime.state("portal") == LifecycleState.RUNNING

    asyncio.run(runtime.stop())
    assert calls[-3:] == ["stop:portal", "stop:evidence", "stop:identity"]
    assert runtime.state("identity") == LifecycleState.STOPPED


def test_start_failure_marks_service_failed_and_stops_started_services() -> None:
    calls: list[str] = []
    registry = ServiceRegistry()
    registry.register(FakeService("identity", calls=calls))
    registry.register(
        FakeService(
            "evidence",
            dependencies=("identity",),
            fail_start=True,
            calls=calls,
        )
    )
    runtime = RuntimeCoordinator(registry)

    with pytest.raises(RuntimeError, match="start failed"):
        asyncio.run(runtime.start())

    assert runtime.state("evidence") == LifecycleState.FAILED
    assert runtime.state("identity") == LifecycleState.STOPPED
    assert calls == ["start:identity", "start:evidence", "stop:identity"]


def test_health_aggregation_reports_degraded() -> None:
    registry = ServiceRegistry()
    registry.register(FakeService("identity"))
    registry.register(
        FakeService(
            "evidence",
            dependencies=("identity",),
            health_status=HealthStatus.DEGRADED,
        )
    )
    runtime = RuntimeCoordinator(registry)
    asyncio.run(runtime.start())

    report = asyncio.run(runtime.health())
    assert report.status == HealthStatus.DEGRADED
    assert report.metrics == {"identity": "healthy", "evidence": "degraded"}


def test_import_and_construction_have_no_runtime_side_effects() -> None:
    registry = ServiceRegistry()
    runtime = RuntimeCoordinator(registry)
    assert runtime.events == ()
    assert runtime.diagnostics()["event_count"] == 0
