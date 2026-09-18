# Implements specs/001-data-model-registry/spec.md.
#
# Every table here is the Approved Sources Registry and everything built on top of it.
# The retrieval boundary the whole system enforces (specs/000, docs/02-architecture.md)
# comes from `chunks` only ever pointing at a row in `sources` that a curator-admin
# approved — nothing else is ever retrievable.

import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base

EMBEDDING_DIM = 384  # sentence-transformers/all-MiniLM-L6-v2 — specs/000


def _uuid():
    return uuid.uuid4()


class SourceCategory(str, enum.Enum):
    statistical_release = "Statistical Release"
    publication = "Publication"
    press_statement = "Press Statement"
    faq = "FAQ"
    historical_communication = "Historical Communication"


class ConfidentialityTag(str, enum.Enum):
    public = "Public"
    internal = "Internal"


class UserRole(str, enum.Enum):
    public = "public"
    media = "media"
    comms_official = "comms_official"
    curator_admin = "curator_admin"


class QueryChannel(str, enum.Enum):
    public = "public"
    media = "media"


class QueryStatus(str, enum.Enum):
    answered = "answered"
    escalated = "escalated"
    approved = "approved"
    rejected = "rejected"


class ReviewDecision(str, enum.Enum):
    approve = "approve"
    edit_approve = "edit_approve"
    reject = "reject"


class TerminologyCategory(str, enum.Enum):
    terminology = "Terminology"
    style_rule = "Style Rule"
    branding_standard = "Branding Standard"
    preferred_phrasing = "Preferred Phrasing"
    prohibited_term = "Prohibited Term"


class Source(Base):
    """The Approved Sources Registry. docs/02-architecture.md Section 4."""

    __tablename__ = "sources"

    source_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    category = Column(Enum(SourceCategory), nullable=False)
    published_date = Column(Date, nullable=False)
    ingested_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    superseded_by = Column(UUID(as_uuid=True), ForeignKey("sources.source_id"), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    confidentiality_tag = Column(Enum(ConfidentialityTag), default=ConfidentialityTag.public, nullable=False)
    checksum = Column(String, nullable=False)
    retention_review_date = Column(Date, nullable=True)

    chunks = relationship("Chunk", back_populates="source")


class Chunk(Base):
    __tablename__ = "chunks"

    chunk_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.source_id"), nullable=False)
    text = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)
    page_number = Column(Integer, nullable=True)
    char_start = Column(Integer, nullable=True)
    char_end = Column(Integer, nullable=True)

    source = relationship("Source", back_populates="chunks")


class User(Base):
    """The 4 fixed demo roles. No self-registration — specs/009-rbac-auth."""

    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    password_hash = Column(String, nullable=True)


class Query(Base):
    __tablename__ = "queries"

    query_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    channel = Column(Enum(QueryChannel), nullable=False)
    text = Column(Text, nullable=False)
    submitted_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    confidence_score = Column(Float, nullable=True)
    status = Column(Enum(QueryStatus), nullable=False)

    drafts = relationship("Draft", back_populates="query")


class Draft(Base):
    __tablename__ = "drafts"

    draft_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    query_id = Column(UUID(as_uuid=True), ForeignKey("queries.query_id"), nullable=False)
    draft_text = Column(Text, nullable=False)
    citations = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    query = relationship("Query", back_populates="drafts")
    reviews = relationship("Review", back_populates="draft")


class Review(Base):
    __tablename__ = "reviews"

    review_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    draft_id = Column(UUID(as_uuid=True), ForeignKey("drafts.draft_id"), nullable=False)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    decision = Column(Enum(ReviewDecision), nullable=False)
    final_text = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    decided_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    draft = relationship("Draft", back_populates="reviews")


class CommunicationMemory(Base):
    __tablename__ = "communication_memory"

    memory_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    query_text = Column(Text, nullable=False)
    final_answer = Column(Text, nullable=False)
    citations = Column(JSON, nullable=False, default=list)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    approved_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class TerminologyGuide(Base):
    """docs/03-security-governance-compliance.md Section 6.1. Dual-control approval
    workflow is a roadmap item for the MVP — see specs/008-curator-admin."""

    __tablename__ = "terminology_guide"

    guide_entry_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    category = Column(Enum(TerminologyCategory), nullable=False)
    term_or_topic = Column(String, nullable=False)
    approved_guidance = Column(Text, nullable=False)
    discouraged_alternative = Column(Text, nullable=True)
    rationale = Column(Text, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    superseded_by = Column(UUID(as_uuid=True), ForeignKey("terminology_guide.guide_entry_id"), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    effective_date = Column(Date, nullable=False)
    last_reviewed_date = Column(Date, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    event_type = Column(String, nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    query_id = Column(UUID(as_uuid=True), ForeignKey("queries.query_id"), nullable=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.source_id"), nullable=True)
    payload = Column(JSON, nullable=True)
    sla_status = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
