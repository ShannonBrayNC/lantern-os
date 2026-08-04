# ADR-001: Lantern Runtime boundary

- Status: Proposed
- Sprint: L1.1
- Issue: #12

## Context

The existing Lantern OS repository currently implements Mission Control, portfolio, revenue, research, milestone, authentication, database, and React application capabilities. ETS Edge requires an appliance runtime with different reliability and dependency constraints.

Renaming or replacing the existing application would create unnecessary product disruption. Embedding appliance lifecycle logic directly in the FastAPI application would also couple device operation to a customer-facing web process.

## Decision

Introduce `lantern_runtime` as an isolated Python package in the existing repository.

The package owns:

- deterministic service registration;
- lifecycle state transitions;
- dependency-ordered startup;
- reverse-order shutdown;
- aggregate health;
- runtime events and diagnostics.

The package does not own:

- ETS protocol semantics;
- evidence canonicalization or verification;
- HTTP routes or React components;
- database persistence;
- collectors;
- cloud synchronization;
- hardware-specific behavior.

`ets-core` will be consumed through its stable public API by a later evidence-engine service. Lantern Runtime will manage that service but will not import protocol internals.

## Runtime invariants

1. Importing `lantern_runtime` performs no I/O and starts no services.
2. Service names are unique.
3. Dependencies must exist before startup planning succeeds.
4. Dependency cycles are rejected.
5. Startup order is deterministic.
6. Shutdown order is the reverse of successful startup.
7. A failed service enters `FAILED` and emits diagnostic evidence.
8. Mission Control remains independently deployable.

## Consequences

The repository temporarily contains two distinct product layers:

- the existing Lantern OS Mission Control application;
- the new Lantern appliance runtime package.

A later repository-structure decision may split them, but L1.1 avoids premature migration and establishes executable boundaries first.

## Follow-on decisions

- L1.2: supervisor, restart policy, watchdog, and process adapters.
- L1.3: signed update manager and rollback.
- L1.4: versioned configuration, secrets, migration, and backup/restore.
