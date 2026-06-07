import secrets
from dataclasses import dataclass
from typing import Dict, Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import AUTH_USERS


ROLE_PERMISSIONS = {
    "operator": {"validation"},
    "admin": {"validation", "ingestion", "reporting", "users"},
}


@dataclass(frozen=True)
class AuthUser:
    username: str
    password: str
    role: str
    display_name: str

    @property
    def permissions(self) -> list[str]:
        return sorted(ROLE_PERMISSIONS.get(self.role, set()))


security = HTTPBearer(auto_error=False)
TOKEN_STORE: Dict[str, AuthUser] = {}


def _load_users() -> Dict[str, AuthUser]:
    users: Dict[str, AuthUser] = {}
    for raw_entry in AUTH_USERS.split(","):
        entry = raw_entry.strip()
        if not entry or "=" not in entry:
            continue

        username, raw_details = entry.split("=", 1)
        parts = raw_details.split(":", 2)
        if len(parts) != 3:
            continue

        password, role, display_name = [part.strip() for part in parts]
        role = role.lower()
        if role not in ROLE_PERMISSIONS:
            continue

        username = username.strip()
        users[username] = AuthUser(
            username=username,
            password=password,
            role=role,
            display_name=display_name,
        )
    return users


AUTH_USER_STORE = _load_users()


def authenticate_user(username: str, password: str) -> AuthUser | None:
    user = AUTH_USER_STORE.get(username.strip())
    if not user or not secrets.compare_digest(user.password, password):
        return None
    return user


def create_user(username: str, password: str, role: str, display_name: str) -> AuthUser:
    username = username.strip()
    role = role.strip().lower()
    display_name = display_name.strip()

    if not username:
        raise ValueError("Username is required.")
    if username in AUTH_USER_STORE:
        raise ValueError("A user with this username already exists.")
    if role not in ROLE_PERMISSIONS:
        raise ValueError("Unsupported role selected.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    if not display_name:
        raise ValueError("Display name is required.")

    user = AuthUser(
        username=username,
        password=password,
        role=role,
        display_name=display_name,
    )
    AUTH_USER_STORE[username] = user
    return user


def list_users() -> list[AuthUser]:
    return sorted(AUTH_USER_STORE.values(), key=lambda user: user.username)


def create_access_token(user: AuthUser) -> str:
    token = secrets.token_urlsafe(32)
    TOKEN_STORE[token] = user
    return token


def serialize_user(user: AuthUser) -> dict:
    return {
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "permissions": user.permissions,
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthUser:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    user = TOKEN_STORE.get(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        )
    return user


def require_permissions(required_permissions: Iterable[str]):
    required = set(required_permissions)

    def dependency(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        allowed = set(user.permissions)
        if not required.issubset(allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role does not have access to this resource.",
            )
        return user

    return dependency
