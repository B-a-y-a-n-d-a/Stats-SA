# Implements specs/009-rbac-auth/spec.md — branch feature/009-rbac-auth.
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.passwords import verify_password
from app.core.security import CurrentUser, create_access_token, get_current_user
from app.db.models import User, UserRole
from app.db.session import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    # Plain str, not EmailStr: the seeded demo accounts live on the special-use
    # `.local` domain, which email-validator rejects (specs/001 seed.py).
    email: str = Field(max_length=320)
    password: str = Field(max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: str
    name: str


class MeResponse(BaseModel):
    user_id: str
    role: UserRole


# POST /api/auth/login — issues a JWT for one of the 4 seeded demo accounts.
@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    return LoginResponse(
        access_token=create_access_token(user_id=str(user.user_id), role=user.role),
        role=user.role,
        user_id=str(user.user_id),
        name=user.name,
    )


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser = Depends(get_current_user)) -> MeResponse:
    return MeResponse(user_id=user.user_id, role=user.role)
