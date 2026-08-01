# Lantern OS

Lantern OS is the operating command center for Lantern Protocol and ETS commercialization.

## Current foundation

- FastAPI application and REST API
- Mission Control dashboard
- Daily task execution with persistent SQLite storage
- Revenue, research, and roadmap summary panels
- Windows, Linux, and Docker startup paths
- Automated smoke and task-lifecycle tests
- GitHub Actions validation on Python 3.12 and 3.13

## Windows

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run.ps1
```

Open `http://localhost:8000`. API documentation is at `http://localhost:8000/docs`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Architecture direction

This first production foundation deliberately avoids the Starlette/Jinja positional-signature failure from the prototype. The UI is server-rendered directly by FastAPI while the API remains separable for a future React/TypeScript client.
