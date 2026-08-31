import secrets
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from fener.config import settings

bearer = HTTPBearer(auto_error=False)


def require_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    configured = settings().fener_admin_key.get_secret_value()
    if not configured:
        raise HTTPException(503, "Private API disabled: configure FENER_ADMIN_KEY")
    if credentials is None or not secrets.compare_digest(configured, credentials.credentials):
        raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
