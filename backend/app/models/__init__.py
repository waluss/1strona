import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Float, ForeignKey, Text, UniqueConstraint, Index, Table
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    profiles = relationship("ContractorProfile", back_populates="tenant", cascade="all, delete-orphan")
    tenders = relationship("Tender", back_populates="tenant", cascade="all, delete-orphan")
    import_runs = relationship("ImportRun", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    username = Column(String(255), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    must_change_password = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", back_populates="users")


class ContractorProfile(Base):
    __tablename__ = "contractor_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="candidate")  # active, candidate, archived
    competencies = Column(JSONB, nullable=False, default=list)
    keywords = Column(JSONB, nullable=False, default=list)
    exclusions = Column(JSONB, nullable=False, default=list)
    regions = Column(JSONB, nullable=False, default=list)
    cpv_codes = Column(JSONB, nullable=False, default=list)
    scoring_rules = Column(JSONB, nullable=False, default=dict)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", back_populates="profiles")
    scores = relationship("TenderScore", back_populates="profile", cascade="all, delete-orphan")


class Tender(Base):
    __tablename__ = "tenders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    source_system = Column(String(50), nullable=False, index=True)
    source_proceeding_id = Column(String(255), nullable=False, index=True)
    title = Column(Text, nullable=False)
    buyer_name = Column(String(500), nullable=True)
    buyer_nip = Column(String(50), nullable=True)
    status = Column(String(50), nullable=True)
    submission_deadline_at = Column(DateTime(timezone=True), nullable=True, index=True)
    location_voivodeship = Column(String(100), nullable=True)
    cpv_codes = Column(JSONB, nullable=False, default=list)
    estimated_value_net = Column(Float, nullable=True)
    raw_notice = Column(JSONB, nullable=True)
    current_notice_id = Column(UUID(as_uuid=True), nullable=True)
    source_published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    requires_scoring = Column(Boolean, default=True, nullable=False)
    view_version = Column(String(50), nullable=False, default="1.0")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", back_populates="tenders")
    notices = relationship("TenderNotice", back_populates="tender", cascade="all, delete-orphan")
    scores = relationship("TenderScore", back_populates="tender", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("source_system", "source_proceeding_id", name="uq_tender_source_system_proceeding"),
    )


class TenderNotice(Base):
    __tablename__ = "tender_notices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    source_system = Column(String(50), nullable=False, index=True)
    notice_id = Column(String(255), nullable=False, index=True)
    notice_number = Column(String(255), nullable=True)
    notice_kind = Column(String(100), nullable=True)
    raw_json = Column(JSONB, nullable=False)
    payload_hash = Column(String(64), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    fetched_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    is_delta = Column(Boolean, default=False, nullable=False)
    needs_review = Column(Boolean, default=False, nullable=False)
    review_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tender = relationship("Tender", back_populates="notices")
    revisions = relationship("TenderNoticeRevision", back_populates="tender_notice", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("source_system", "notice_id", name="uq_notice_source_system_notice_id"),
    )


class TenderNoticeRevision(Base):
    __tablename__ = "tender_notice_revisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_notice_id = Column(UUID(as_uuid=True), ForeignKey("tender_notices.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_payload_hash = Column(String(64), nullable=False)
    previous_raw_json = Column(JSONB, nullable=False)
    changed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    change_reason = Column(Text, nullable=True)

    tender_notice = relationship("TenderNotice", back_populates="revisions")


class TenderScore(Base):
    __tablename__ = "tender_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    contractor_profile_id = Column(UUID(as_uuid=True), ForeignKey("contractor_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, nullable=False)
    decision = Column(String(50), nullable=False)  # MATCH, REJECT, MANUAL_REVIEW
    breakdown = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    scoring_version = Column(String(50), nullable=False, default="1.0")

    tender = relationship("Tender", back_populates="scores")
    profile = relationship("ContractorProfile", back_populates="scores")


class ImportRun(Base):
    __tablename__ = "import_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    source_system = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")  # PENDING, RUNNING, COMPLETED, FAILED
    params = Column(JSONB, nullable=True)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    statistics = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)

    tenant = relationship("Tenant", back_populates="import_runs")
