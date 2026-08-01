# Lantern OS Authentication

Lantern OS supports two explicit authentication modes.

## Local development

`LANTERN_AUTH_MODE=local` is the default. The application creates a synthetic local principal from environment variables and never contacts an external identity provider.

Supported local roles:

- `Owner`
- `Executive`
- `Operator`
- `Viewer`

Use local mode only for development and isolated testing.

## Microsoft Entra ID

Set `LANTERN_AUTH_MODE=entra` and configure:

- `LANTERN_SESSION_SECRET`: at least 32 random characters
- `LANTERN_ENTRA_TENANT_ID`
- `LANTERN_ENTRA_CLIENT_ID`
- `LANTERN_ENTRA_CLIENT_SECRET`
- `LANTERN_ENTRA_REDIRECT_URI`
- `LANTERN_ENTRA_DEFAULT_ROLE`

Register the redirect URI `/auth/callback` in the Entra application. The OIDC flow requests `openid profile email`.

## Role model

| Role | Access |
|---|---|
| Viewer | Read dashboards, tasks, KPIs, settings, and recommendations |
| Operator | Viewer access plus task and KPI mutation |
| Executive | Operator access plus organization and strategy settings |
| Owner | Full application authority |

Entra application roles should use the exact values above. When multiple roles are present, Lantern OS selects the highest-authority role. When no mapped role is present, `LANTERN_ENTRA_DEFAULT_ROLE` is used and defaults to `Viewer`.

## Security controls

- Production Entra mode refuses to start with a session secret shorter than 32 characters.
- Mutation endpoints enforce role dependencies server-side.
- Session cookies use `SameSite=Lax`.
- Set `LANTERN_COOKIE_HTTPS_ONLY=true` in HTTPS deployments.
- Secrets must be supplied through environment configuration or a secret store and must never be committed.

## Validation

Check the authenticated identity:

```powershell
Invoke-RestMethod http://localhost:8000/api/me
```

Check runtime mode:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```
