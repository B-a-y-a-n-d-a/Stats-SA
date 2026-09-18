# Implements specs/010-audit-log/spec.md — branch feature/010-audit-log.
#
# log_event(event_type, actor_id=None, query_id=None, source_id=None, payload=None,
# sla_status=None) writes one row to `audit_log`. This signature is fixed: 004/005/006/008
# already call it with these exact keyword args and no `db` argument (see
# app/api/public_query.py), so it opens and closes its own short-lived session rather
# than accepting one from the caller.
#
# Hard acceptance criterion (specs/010): a logging failure must never raise out of this
# function and break the caller's actual request. Every code path here is wrapped in a
# broad try/except that swallows the exception and prints a warning to stderr as a
# stand-in for real alerting (no alerting pipeline exists in this hackathon build).
import sys

from app.db.models import AuditLog
from app.db.session import SessionLocal


def log_event(event_type: str, actor_id=None, query_id=None, source_id=None, payload=None, sla_status=None):
    try:
        db = SessionLocal()
        try:
            db.add(
                AuditLog(
                    event_type=event_type,
                    actor_id=actor_id,
                    query_id=query_id,
                    source_id=source_id,
                    payload=payload,
                    sla_status=sla_status,
                )
            )
            db.commit()
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001 — deliberately broad, see module docstring.
        print(f"[audit] WARNING: failed to write audit log event {event_type!r}: {exc!r}", file=sys.stderr)
