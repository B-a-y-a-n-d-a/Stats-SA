"""Add sources.retired_at for source retirement

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-18

Implements specs/008-curator-admin/spec.md: DELETE /api/curator/sources/{id}
retires a source (marks it non-retrievable, does not hard-delete) by setting
this column. See backend/app/db/models.py (Source.retired_at) and
backend/app/retrieval/search.py, which excludes retired sources from search.
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("sources", sa.Column("retired_at", sa.DateTime, nullable=True))


def downgrade():
    op.drop_column("sources", "retired_at")
