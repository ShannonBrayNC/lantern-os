# Lantern OS database migration runbook

## Supported profiles

Lantern OS uses `LANTERN_DATABASE_URL` for all persistence.

Local SQLite default:

```text
sqlite:///data/lantern.db
```

PostgreSQL example:

```text
postgresql+psycopg://lantern:lantern@localhost:5432/lantern
```

## Fresh PostgreSQL deployment

```powershell
$env:LANTERN_DATABASE_URL = "postgresql+psycopg://lantern:lantern@localhost:5432/lantern"
alembic upgrade head
python -m scripts.seed
.\run.ps1
```

With Docker:

```powershell
docker compose up --build
```

The application container waits for PostgreSQL health, runs `alembic upgrade head`, and then starts Uvicorn.

## Transfer existing SQLite data

1. Stop Lantern OS.
2. Back up `data/lantern.db`.
3. Start an empty PostgreSQL database.
4. Apply migrations.
5. Run the transfer utility.

```powershell
Copy-Item .\data\lantern.db .\data\lantern-before-postgres.db

$target = "postgresql+psycopg://lantern:lantern@localhost:5432/lantern"
$env:LANTERN_DATABASE_URL = $target
alembic upgrade head

python -m scripts.transfer_database `
  --source "sqlite:///data/lantern.db" `
  --target $target
```

Validate before cutover:

```powershell
$env:LANTERN_DATABASE_URL = $target
python -m pytest -q
python -m scripts.seed
.\run.ps1
```

Confirm `/api/health` reports `database: postgresql` and verify task, KPI, pipeline, research, and milestone counts.

## Rollback

The rollback boundary for this release is the database connection string.

1. Stop Lantern OS.
2. Restore `LANTERN_DATABASE_URL` to the SQLite URL or remove the variable.
3. Restore `data/lantern.db` from the pre-cutover copy if required.
4. Start Lantern OS and confirm `/api/health` reports `database: sqlite`.

Do not run `alembic downgrade` as a data-recovery mechanism. Use a PostgreSQL backup or snapshot for database-level rollback.

## Backup requirements

Before every production migration:

- Capture a PostgreSQL logical backup or managed-service restore point.
- Preserve the current application image or commit SHA.
- Record the current Alembic revision with `alembic current`.
- Test restore and startup in a non-production environment.
