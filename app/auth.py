from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Callable

from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, HTTPException, Request, status

ROLE_ORDER = {"Viewer": 0, "Operator": 1, "Executive": 2, "Owner": 3}


@dataclass(frozen=True)
class Principal:
    subject: str
    name: str
    email: str
    role: str
    source: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def auth_mode() -> str:
    return os.getenv("LANTERN_AUTH_MODE", "local").strip().lower()


def session_secret() -> str:
    value = os.getenv("LANTERN_SESSION_SECRET", "")
    if auth_mode() == "entra" and len(value) < 32:
        raise RuntimeError("LANTERN_SESSION_SECRET must contain at least 32 characters in Entra mode")
    return value or "lantern-local-development-secret-only"


def local_principal() -> Principal:
    role = os.getenv("LANTERN_LOCAL_ROLE", "Owner")
    if role not in ROLE_ORDER:
        role = "Viewer"
    return Principal(
        subject="local-development-user",
        name=os.getenv("LANTERN_LOCAL_NAME", "Lantern Owner"),
        email=os.getenv("LANTERN_LOCAL_EMAIL", "owner@localhost"),
        role=role,
        source="local",
    )


def build_oauth() -> OAuth:
    oauth = OAuth()
    if auth_mode() != "entra":
        return oauth
    tenant = os.environ["LANTERN_ENTRA_TENANT_ID"]
    client_id = os.environ["LANTERN_ENTRA_CLIENT_ID"]
    client_secret = os.environ["LANTERN_ENTRA_CLIENT_SECRET"]
    oauth.register(
        name="entra",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url=f"https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration",
        client_kwargs={"scope": "openid profile email"},
    )
    return oauth


def principal_from_claims(claims: dict) -> Principal:
    configured = [str(role) for role in claims.get("roles", []) if str(role) in ROLE_ORDER]
    role = max(configured, key=lambda item: ROLE_ORDER[item]) if configured else os.getenv("LANTERN_ENTRA_DEFAULT_ROLE", "Viewer")
    if role not in ROLE_ORDER:
        role = "Viewer"
    return Principal(
        subject=str(claims.get("sub") or claims.get("oid") or "unknown"),
        name=str(claims.get("name") or claims.get("preferred_username") or "Lantern User"),
        email=str(claims.get("email") or claims.get("preferred_username") or ""),
        role=role,
        source="entra",
    )


def current_principal(request: Request) -> Principal:
    if auth_mode() == "local":
        return local_principal()
    payload = request.session.get("principal")
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return Principal(**payload)


def require_roles(*allowed: str) -> Callable:
    minimum = max((ROLE_ORDER[role] for role in allowed), default=0)

    def dependency(principal: Principal = Depends(current_principal)) -> Principal:
        if ROLE_ORDER.get(principal.role, -1) < minimum:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return principal

    return dependency
