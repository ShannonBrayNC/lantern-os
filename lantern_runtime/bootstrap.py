"""Deterministic Lantern Runtime bootstrap and shutdown coordination."""

from __future__ import annotations

from dataclasses import dataclass, field

from lantern_runtime.models import (
    HealthReport,
    HealthStatus,
    LifecycleState,
    RuntimeEvent,
    RuntimeService,
)
from lantern_runtime.registry import ServiceRegistry


@dataclass(slots=True)
class ServiceRuntimeState:
    service: RuntimeService
    state: LifecycleState = LifecycleState.NEW
    error: str | None = None


@dataclass(slots=True)
class RuntimeCoordinator:
    registry: ServiceRegistry
    _states: dict[str, ServiceRuntimeState] = field(default_factory=dict, init=False)
    _started: list[str] = field(default_factory=list, init=False)
    _events: list[RuntimeEvent] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._states = {
            service.descriptor.name: ServiceRuntimeState(service=service)
            for service in self.registry.services()
        }

    @property
    def events(self) -> tuple[RuntimeEvent, ...]:
        return tuple(self._events)

    def state(self, service_name: str) -> LifecycleState:
        return self._states[service_name].state

    async def start(self) -> None:
        for service in self.registry.startup_order():
            name = service.descriptor.name
            self._transition(name, LifecycleState.INITIALIZING)
            self._transition(name, LifecycleState.STARTING)
            try:
                await service.start()
            except Exception as exc:
                self._states[name].error = f"{type(exc).__name__}: {exc}"
                self._transition(name, LifecycleState.FAILED, self._states[name].error or "")
                await self._stop_started_services()
                raise
            self._started.append(name)
            self._transition(name, LifecycleState.RUNNING)

    async def stop(self) -> None:
        await self._stop_started_services()

    async def health(self) -> HealthReport:
        reports: list[HealthReport] = []
        for name in self._started:
            reports.append(await self._states[name].service.health())

        if any(report.status == HealthStatus.FAILED for report in reports):
            status = HealthStatus.FAILED
        elif any(report.status in {HealthStatus.DEGRADED, HealthStatus.UNKNOWN} for report in reports):
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY

        return HealthReport(
            service="lantern-runtime",
            status=status,
            detail=f"{len(reports)} managed service(s)",
            metrics={report.service: report.status.value for report in reports},
        )

    def diagnostics(self) -> dict[str, object]:
        return {
            "services": {
                name: {
                    "state": runtime_state.state.value,
                    "error": runtime_state.error,
                }
                for name, runtime_state in sorted(self._states.items())
            },
            "startup_order": tuple(self._started),
            "event_count": len(self._events),
        }

    async def _stop_started_services(self) -> None:
        while self._started:
            name = self._started.pop()
            runtime_state = self._states[name]
            self._transition(name, LifecycleState.STOPPING)
            try:
                await runtime_state.service.stop()
            except Exception as exc:
                runtime_state.error = f"{type(exc).__name__}: {exc}"
                self._transition(name, LifecycleState.FAILED, runtime_state.error)
                continue
            self._transition(name, LifecycleState.STOPPED)

    def _transition(self, name: str, state: LifecycleState, detail: str = "") -> None:
        self._states[name].state = state
        self._events.append(
            RuntimeEvent(
                sequence=len(self._events) + 1,
                kind="lifecycle",
                service=name,
                state=state,
                detail=detail,
            )
        )
