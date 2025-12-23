from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext

from .config import get_settings

security = HTTPBasic()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminUser:
    def __init__(self, username: str, password_hash: str, must_reset: bool):
        self.username = username
        self.password_hash = password_hash
        self.must_reset = must_reset


_admin_cache: Optional[AdminUser] = None


def get_admin_user() -> AdminUser:
    global _admin_cache
    settings = get_settings()
    if _admin_cache:
        return _admin_cache
    _admin_cache = AdminUser(
        username=settings.admin_username,
        password_hash=pwd_context.hash(settings.admin_password),
        must_reset=True,
    )
    return _admin_cache


def authenticate(credentials: HTTPBasicCredentials = Depends(security)) -> AdminUser:
    admin = get_admin_user()
    correct_username = credentials.username == admin.username
    correct_password = pwd_context.verify(credentials.password, admin.password_hash)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return admin


def update_password(new_password: str) -> None:
    admin = get_admin_user()
    admin.password_hash = pwd_context.hash(new_password)
    admin.must_reset = False


def require_password_reset(admin: AdminUser = Depends(authenticate)) -> AdminUser:
    if admin.must_reset:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Password change required")
    return admin
