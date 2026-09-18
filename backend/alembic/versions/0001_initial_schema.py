"""Initial schema - Approved Sources Registry and dependent tables

Revision ID: 0001
Revises:
Create Date: 2026-09-18

Implements specs/001-data-model-registry/spec.md. See backend/app/db/models.py for
the SQLAlchemy models this mirrors field-for-field.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 384


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("email", sa.String, nullable=False, unique=True),
        sa.Column(
            "role",
            sa.Enum("public", "media", "comms_official", "curator_admin", name="userrole"),
            nullable=False,
        ),
        sa.Column("password_hash", sa.String, nullable=True),
    )

    op.create_table(
        "sources",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("url", sa.String, nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "Statistical Release",
                "Publication",
                "Press Statement",
                "FAQ",
                "Historical Communication",
                name="sourcecategory",
            ),
            nullable=False,
        ),
        sa.Column("published_date", sa.Date, nullable=False),
        sa.Column("ingested_date", sa.DateTime, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("superseded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.source_id"), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column(
            "confidentiality_tag",
            sa.Enum("Public", "Internal", name="confidentialitytag"),
            nullable=False,
            server_default="Public",
        ),
        sa.Column("checksum", sa.String, nullable=False),
        sa.Column("retention_review_date", sa.Date, nullable=True),
    )

    op.create_table(
        "chunks",
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.source_id"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("page_number", sa.Integer, nullable=True),
        sa.Column("char_start", sa.Integer, nullable=True),
        sa.Column("char_end", sa.Integer, nullable=True),
    )

    op.create_table(
        "queries",
        sa.Column("query_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("channel", sa.Enum("public", "media", name="querychannel"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("submitted_at", sa.DateTime, nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column(
            "status",
            sa.Enum("answered", "escalated", "approved", "rejected", name="querystatus"),
            nullable=False,
        ),
    )

    op.create_table(
        "drafts",
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("query_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("queries.query_id"), nullable=False),
        sa.Column("draft_text", sa.Text, nullable=False),
        sa.Column("citations", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "reviews",
        sa.Column("review_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drafts.draft_id"), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column(
            "decision",
            sa.Enum("approve", "edit_approve", "reject", name="reviewdecision"),
            nullable=False,
        ),
        sa.Column("final_text", sa.Text, nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("decided_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "communication_memory",
        sa.Column("memory_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("query_text", sa.Text, nullable=False),
        sa.Column("final_answer", sa.Text, nullable=False),
        sa.Column("citations", sa.JSON, nullable=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("approved_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "terminology_guide",
        sa.Column("guide_entry_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "category",
            sa.Enum(
                "Terminology",
                "Style Rule",
                "Branding Standard",
                "Preferred Phrasing",
                "Prohibited Term",
                name="terminologycategory",
            ),
            nullable=False,
        ),
        sa.Column("term_or_topic", sa.String, nullable=False),
        sa.Column("approved_guidance", sa.Text, nullable=False),
        sa.Column("discouraged_alternative", sa.Text, nullable=True),
        sa.Column("rationale", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "superseded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("terminology_guide.guide_entry_id"),
            nullable=True,
        ),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("effective_date", sa.Date, nullable=False),
        sa.Column("last_reviewed_date", sa.Date, nullable=True),
    )

    op.create_table(
        "audit_log",
        sa.Column("log_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String, nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("query_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("queries.query_id"), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.source_id"), nullable=True),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column("sla_status", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )


def downgrade():
    op.drop_table("audit_log")
    op.drop_table("terminology_guide")
    op.drop_table("communication_memory")
    op.drop_table("reviews")
    op.drop_table("drafts")
    op.drop_table("queries")
    op.drop_table("chunks")
    op.drop_table("sources")
    op.drop_table("users")
    for enum_name in (
        "userrole",
        "sourcecategory",
        "confidentialitytag",
        "querychannel",
        "querystatus",
        "reviewdecision",
        "terminologycategory",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
