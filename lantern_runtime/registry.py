"""Deterministic Lantern Runtime service registry."""

from __future__ import annotations

from collections.abc import Iterable

from lantern_runtime.models import RuntimeService


class ServiceRegistryError(RuntimeError):
    """Base registry error."""


class DuplicateServiceError(ServiceRegistryError):
    """A service name is already registered."""


class MissingDependencyError(ServiceRegistryError):
    """A service references an unregistered dependency."""


class DependencyCycleError(ServiceRegistryError):
    """The registered dependency graph contains a cycle."""


class ServiceRegistry:
    def __init__(self) -> None:
        self._services: dict[str, RuntimeService] = {}

    def register(self, service: RuntimeService) -> None:
        name = service.descriptor.name
        if name in self._services:
            raise DuplicateServiceError(f"service already registered: {name}")
        self._services[name] = service

    def get(self, name: str) -> RuntimeService:
        return self._services[name]

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._services))

    def services(self) -> tuple[RuntimeService, ...]:
        return tuple(self._services[name] for name in self.names())

    def startup_order(self) -> tuple[RuntimeService, ...]:
        self._validate_dependencies()
        visiting: set[str] = set()
        visited: set[str] = set()
        ordered: list[str] = []

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in visiting:
                raise DependencyCycleError(f"dependency cycle includes: {name}")
            visiting.add(name)
            service = self._services[name]
            dependencies = sorted(service.descriptor.dependencies)
            for dependency in dependencies:
                visit(dependency)
            visiting.remove(name)
            visited.add(name)
            ordered.append(name)

        candidates = sorted(
            self._services,
            key=lambda name: (
                self._services[name].descriptor.startup_priority,
                name,
            ),
        )
        for name in candidates:
            visit(name)
        return tuple(self._services[name] for name in ordered)

    def _validate_dependencies(self) -> None:
        missing: list[tuple[str, str]] = []
        for service in self._services.values():
            for dependency in service.descriptor.dependencies:
                if dependency not in self._services:
                    missing.append((service.descriptor.name, dependency))
        if missing:
            details = ", ".join(f"{service}->{dependency}" for service, dependency in sorted(missing))
            raise MissingDependencyError(f"missing dependencies: {details}")

    def extend(self, services: Iterable[RuntimeService]) -> None:
        for service in services:
            self.register(service)
