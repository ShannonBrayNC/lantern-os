# Lantern Mission Control

This repository contains Lantern Mission Control, the business and program operating application for Lantern Protocol commercialization.

It owns:

- daily execution and task management;
- revenue pipeline and KPI scorecards;
- research-commercialization tracking;
- engineering portfolio visibility;
- milestone, settings, and recommendation workflows;
- the Mission Control FastAPI and React application.

It does **not** own the ETS Edge appliance operating system, appliance runtime, local appliance portal, image construction, systemd packaging, device identity, collectors, synchronization agent, update/rollback implementation, or physical-hardware acceptance.

The authoritative ETS Edge appliance repository is:

`Lantern-Protocol/Operating-System`

The authoritative ETS protocol and core library repository is:

`ShannonBrayNC/ETS`

The proposed `lantern_runtime` prototype from issue #12 and PR #13 is retired from this repository. Its accepted design concepts are tracked for implementation in `Lantern-Protocol/Operating-System` issue #79.

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
