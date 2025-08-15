# app/security.py
from fastapi import Header, HTTPException, status
from .config import settings

def require_admin(authorization: str | None = Header(None)):
    expected = f"Bearer {settings.ADMIN_TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
