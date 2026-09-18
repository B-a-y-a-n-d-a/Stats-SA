# Implements specs/010-audit-log/spec.md — branch feature/010-audit-log.
#
# GET /api/audit — lists audit_log rows, newest first, optionally filtered by
# query_id and/or an inclusive created_at date range. Restricted to
# comms_official and curator_admin (specs/010 acceptance criteria: inaccessible
# to public/media) via the real require_role dependency (specs/009, merged).
import uuid
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.models import AuditLog
from app.db.session import get_db

router = APIRouter(prefix="/api/audit", tags=["audit"])


def _serialize(log: AuditLog) -> dict:
    return {
        "log_id": str(log.log_id),
        "event_type": log.event_type,
        "actor_id": str(log.actor_id) if log.actor_id else None,
        "query_id": str(log.query_id) if log.query_id else None,
        "source_id": str(log.source_id) if log.source_id else None,
        "payload": log.payload,
        "sla_status": log.sla_status,
        "created_at": log.created_at.isoformat(),
    }


@router.get("")
def list_audit_log(
    query_id: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user=Depends(require_role("comms_official", "curator_admin")),
):
    q = db.query(AuditLog)

    if query_id:
        try:
            query_uuid = uuid.UUID(query_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="query_id must be a valid UUID.")
        # Filtered as a uuid.UUID (not the raw string) so this also works against the
        # SQLite engine tests use — the UUID column type's bind processor requires a
        # real UUID object when the underlying DB has no native UUID type.
        q = q.filter(AuditLog.query_id == query_uuid)

    if start_date:
        try:
            start_dt = datetime.combine(date.fromisoformat(start_date), time.min)
        except ValueError:
            raise HTTPException(status_code=400, detail="start_date must be an ISO date string (YYYY-MM-DD).")
        q = q.filter(AuditLog.created_at >= start_dt)

    if end_date:
        try:
            end_dt = datetime.combine(date.fromisoformat(end_date), time.max)
        except ValueError:
            raise HTTPException(status_code=400, detail="end_date must be an ISO date string (YYYY-MM-DD).")
        q = q.filter(AuditLog.created_at <= end_dt)

    logs = q.order_by(AuditLog.created_at.desc()).all()
    return [_serialize(log) for log in logs]
