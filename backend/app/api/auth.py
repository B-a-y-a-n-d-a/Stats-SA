# Implements specs/009-rbac-auth/spec.md — branch feature/009-rbac-auth.
from fastapi import APIRouter

router = APIRouter(prefix="/api/auth", tags=["auth"])

# POST /api/auth/login — issues a JWT for one of the 4 seeded demo accounts.
