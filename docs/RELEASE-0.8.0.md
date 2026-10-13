# Lantern OS 0.8.0 Release Candidate

## Release objective

Promote Lantern OS from a server-rendered internal console to an integrated application foundation with a production React interface, authenticated FastAPI services, portable persistence, and observable engineering health.

## Included

- Mission Control operating data for tasks, revenue, research, milestones, settings, KPIs, and recommendations.
- Microsoft Entra ID authentication, local development authentication, and Viewer, Operator, Executive, and Owner authorization boundaries.
- SQLAlchemy persistence with SQLite and PostgreSQL support.
- Alembic migrations, seeding, and transfer tooling.
- Failure-isolated, cached GitHub engineering portfolio health.
- React and TypeScript application shell with a typed API client.
- Multi-stage production container that builds the frontend and serves a single deployable application.
- Production SPA fallback that excludes API, authentication, OpenAPI, and documentation routes.
- `/legacy` rollback route for the existing server-rendered Mission Control dashboard.
- CI gates for Python 3.12 and 3.13, PostgreSQL migrations, frontend lint/tests/build, and integrated container smoke validation.

## Required validation

The release candidate is acceptable only when all of the following checks pass on the pull request and the final `main` commit:

1. `Backend / Python 3.12`
2. `Backend / Python 3.13`
3. `PostgreSQL migration and regression`
4. `Frontend quality gates`
5. `Integrated production serving`

The integrated gate must prove:

- `/` returns the compiled React application.
- `/api/health` reports a healthy service and schema.
- `/docs` remains available.
- `/legacy` renders the rollback dashboard.
- Unknown client-side paths return the React application rather than a backend 404.
- The final container reports healthy through its Docker health check.

## Deployment and rollback

Production starts `app.production:app`. The production wrapper delegates `/api`, `/auth`, `/docs`, `/openapi.json`, and `/redoc` to the FastAPI backend, serves `/assets` from the compiled frontend, and returns `index.html` for client-side routes.

Rollback options:

1. Direct users to `/legacy` while retaining the same deployed image and backend.
2. Start `app.main:app` to bypass React entirely.
3. Redeploy the previously approved container digest.

## Security requirements before external hosting

- Use Entra mode; local authentication must not be enabled in hosted production.
- Store the session secret and Entra credentials in an approved secret manager.
- Require HTTPS-only cookies.
- Restrict trusted hosts and cross-origin access at the ingress layer.
- Enforce PostgreSQL TLS for managed database connections.
- Review whether `/docs` and `/redoc` should be disabled or access-controlled.
- Enable dependency, container, and secret scanning.

## Known remaining gaps

The React client does not yet expose every mutable field available in the legacy dashboard. Issue #10 remains the controlling work item for full Mission Control parity, including revenue pipeline, research, milestones, KPI updates, settings, and complete authorization-specific interaction states.

The production integration, rollback route, release metadata, and CI evidence introduced by this release are intended to make that remaining parity work safe and independently deployable.
