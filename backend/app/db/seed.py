"""Seeds the 4 demo accounts used for the hackathon demo (specs/000, specs/009).

Run with: python -m app.db.seed

Fixed, documented password for demo day only — never do this in a real deployment.
"""
import uuid

from passlib.hash import bcrypt

from app.db.models import User, UserRole
from app.db.session import SessionLocal

DEMO_PASSWORD = "StatsSA-Demo-2026"

DEMO_ACCOUNTS = [
    ("Public Demo User", "public@demo.statssa.local", UserRole.public),
    ("Media Demo User", "media@demo.statssa.local", UserRole.media),
    ("Comms Official Demo", "official@demo.statssa.local", UserRole.comms_official),
    ("Curator Admin Demo", "curator@demo.statssa.local", UserRole.curator_admin),
]


def seed():
    db = SessionLocal()
    try:
        for name, email, role in DEMO_ACCOUNTS:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                continue
            db.add(
                User(
                    user_id=uuid.uuid4(),
                    name=name,
                    email=email,
                    role=role,
                    password_hash=bcrypt.hash(DEMO_PASSWORD),
                )
            )
        db.commit()
        print(f"Seeded {len(DEMO_ACCOUNTS)} demo accounts (password: {DEMO_PASSWORD})")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
