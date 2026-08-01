# Lantern OS

Lantern OS is the operating platform for Lantern Protocol and ETS commercialization.

## Current release

`0.5.0` internal release candidate provides Mission Control, daily execution, revenue pipeline, research commercialization, milestone tracking, persistent settings, KPI scorecards, and actionable recommendations.

## Windows

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run.ps1
```

Open `http://localhost:8000`. API documentation is at `http://localhost:8000/docs`.

## Validation

```powershell
python -m pytest -q
```

See `docs/RELEASE-0.5.0.md` for scope and exit criteria.
