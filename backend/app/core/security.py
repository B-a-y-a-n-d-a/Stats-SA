# Implements specs/009-rbac-auth/spec.md — branch feature/009-rbac-auth.
#
# Will expose: create_access_token(user_id, role), decode_access_token(token),
# and a require_role(role) FastAPI dependency used by review.py, curator.py and audit.py.
