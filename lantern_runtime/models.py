"""Normative Lantern Runtime lifecycle and health contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable


class LifecycleState(StrEnum):
    NEW = "new"
    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class HealthReport:
    service: str
    status: HealthStatus
    detail: str = ""
    metrics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))


@dataclass(frozen=True, slots=True)
class ServiceDescriptor:
    name: str
    version: str
    dependencies: tuple[str, ...] = ()
    startup_priority: int = 100

    def __post_init__(self) -> None:
        if not self.name or self.name.strip() != self.name:
            raise ValueError("service name must be non-empty and trimmed")
        if not self.version:
            raise ValueError("service version must be non-empty")
        if self.name in self.dependencies:
            raise ValueError("service cannot depend on itself")
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError("service dependencies must be unique")


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    sequence: int
    kind: str
    service: str | None
    state: LifecycleState | None
    detail: str = ""


@runtime_checkable
class RuntimeService(Protocol):
    descriptor: ServiceDescriptor

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def health(self) -> HealthReport: ...
