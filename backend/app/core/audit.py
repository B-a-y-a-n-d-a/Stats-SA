# Implements specs/010-audit-log/spec.md — branch feature/010-audit-log.
#
# Will expose log_event(event_type, actor_id=None, query_id=None, source_id=None,
# payload=None, sla_status=None). Build and merge this early — 004/005/006/008 all
# call it from their own branches.


def log_event(event_type: str, **kwargs):
    """Placeholder no-op until feature/010-audit-log lands. Safe to call from any
    branch in the meantime — it just does nothing yet."""
    pass
