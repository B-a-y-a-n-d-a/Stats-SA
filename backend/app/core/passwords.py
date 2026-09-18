# Shared password hashing, used by seed.py now and specs/009-rbac-auth's login
# endpoint later. Uses the `bcrypt` package directly rather than `passlib` —
# passlib's bcrypt backend probes `bcrypt.__about__.__version__`, which modern
# `bcrypt` releases (4.1+) no longer expose, breaking passlib's self-test on
# import. Found via live testing against a real DB (specs/001), not by inspection.
import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
