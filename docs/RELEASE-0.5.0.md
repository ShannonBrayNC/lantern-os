# Lantern OS 0.5.0 Internal Release Candidate

## Release objective

Make Lantern OS useful as the daily operating console for ETS commercialization.

## Included

- Mission Control with pipeline, execution, research, milestone, and KPI views.
- Deterministic daily recommendations based on open P0 work, proposal-stage revenue, and research progress.
- Persistent organization settings and North Star configuration.
- Persistent KPI targets and actuals.
- Versioned schema metadata and backward-compatible SQLite upgrades.
- REST APIs for tasks, settings, KPIs, recommendations, and health.
- Regression coverage for the full dashboard and mutable operating state.

## Exit criteria

- All CI jobs pass on Python 3.12 and 3.13.
- Local Windows startup displays `Loaded Lantern OS 0.5.0`.
- `/`, `/docs`, `/api/health`, `/api/settings`, `/api/kpis`, and `/api/recommendations` return successfully.
- Existing local SQLite records survive upgrade.

## Deferred beyond 0.5.0

- Microsoft Entra ID authentication.
- PostgreSQL and Alembic production migrations.
- Live GitHub portfolio integration.
- React/TypeScript client.
- LLM-generated recommendations and governed AI staff.
