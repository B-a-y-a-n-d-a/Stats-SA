# Implements specs/009-rbac-auth/spec.md — branch feature/009-rbac-auth.
#
# Exposes: create_access_token(user_id, role), decode_access_token(token),
# and a require_role(role) FastAPI dependency used by review.py, curator.py and audit.py.
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.db.models import UserRole

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    """The caller's identity, taken only from a verified JWT — never from a header
    the client controls (specs/009 Acceptance Criteria)."""

    user_id: str
    role: UserRole


def create_access_token(user_id: str, role: UserRole | str) -> str:
    role_value = role.value if isinstance(role, UserRole) else role
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "user_id": str(user_id),
        "role": role_value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expiry_minutes),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> CurrentUser:
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = claims.get("user_id")
    raw_role = claims.get("role")
    try:
        role = UserRole(raw_role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token carries an unknown role",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing a user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return CurrentUser(user_id=user_id, role=role)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_access_token(credentials.credentials)


def require_role(*roles: UserRole | str):
    """FastAPI dependency factory. `Depends(require_role("curator_admin"))` rejects
    any token whose role is not in `roles` with a 403."""

    allowed = {r.value if isinstance(r, UserRole) else r for r in roles}

    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role.value not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This role may not access this resource",
            )
        return user

    return dependency
