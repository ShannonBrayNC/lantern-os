# Lantern OS

Lantern OS is the operating platform for Lantern Protocol and ETS commercialization.

## Current release

`0.8.0` release candidate provides:

- Mission Control for daily execution, revenue pipeline, research commercialization, milestones, and KPI scorecards.
- Microsoft Entra ID authentication with local development mode and role-based authorization.
- SQLite and PostgreSQL persistence with Alembic migrations.
- Read-only GitHub engineering portfolio health.
- React and TypeScript application shell with a typed API client.
- A single production container that serves React, FastAPI APIs, authentication, documentation, and the rollback dashboard.

See `docs/RELEASE-0.8.0.md` for scope, validation gates, and remaining exit criteria.

## Local backend and legacy dashboard

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run.ps1
```

Open `http://localhost:8000`. API documentation is at `http://localhost:8000/docs`.

## React development

Start the backend, then in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

The Vite development server proxies backend requests during frontend development.

## Production container

```powershell
docker build -t lantern-os:0.8.0 .
docker run --rm -p 8000:8000 `
  -e LANTERN_AUTH_MODE=local `
  -e LANTERN_SESSION_SECRET="replace-with-at-least-32-random-characters" `
  lantern-os:0.8.0
```

Production routes:

- `/` — compiled React application
- `/api/*` — FastAPI APIs
- `/auth/*` — authentication flows
- `/docs` — OpenAPI documentation
- `/legacy` — server-rendered rollback dashboard

## Validation

Backend:

```powershell
python -m pytest -q
```

Frontend:

```powershell
cd frontend
npm install
npm run lint
npm test
npm run build
```

Integrated production serving is validated in GitHub Actions by building and starting the container, then checking React, API, documentation, rollback, and SPA fallback routes.
