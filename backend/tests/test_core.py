import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models import Base, Tenant, User, ContractorProfile, Tender, TenderNotice
from app.core.security import get_password_hash, create_access_token
from app.importers.bzp_dto import BzpNoticeDTO
from app.importers.bzp_normalizer import normalize_bzp_notice
from app.services.importer import _canonical_hash, import_notices
from app.services.dry_run_service import execute_bzp_dry_run
from app.scoring.neutral_matcher import match_tender_against_profile

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_canonical_hash():
    payload1 = {"bzpNumber": "2025/BZP 0001", "orderObject": "Water Pipeline"}
    payload2 = {"orderObject": "Water Pipeline", "bzpNumber": "2025/BZP 0001"}
    assert _canonical_hash(payload1) == _canonical_hash(payload2)

def test_bzp_normalizer():
    dto = BzpNoticeDTO(
        bzpNumber="2025/BZP 0001",
        noticeNumber="0001",
        noticeType="OgloszenieOZamowieniu",
        orderObject="Construction of water supply network",
        organizationName="City Waterworks",
        organizationProvince="Mazowieckie",
        cpvCode="45231300-8"
    )
    normalized = normalize_bzp_notice(dto)
    assert normalized.source_system == "BZP"
    assert normalized.title == "Construction of water supply network"
    assert "45231300-8" in normalized.cpv_codes

def test_neutral_matcher():
    match = match_tender_against_profile(
        tender_title="Renovation of sewage system in Warsaw",
        tender_description="Trenchless rehabilitation of water pipeline",
        tender_cpvs=["45231300-8"],
        tender_region="Mazowieckie",
        profile_keywords=["sewage", "water pipeline"],
        profile_exclusions=["gas"],
        profile_cpvs=["45231300-8"],
        profile_regions=["Mazowieckie"]
    )
    assert match.decision == "MATCH"
    assert match.score >= 50.0
    assert "sewage" in match.matched_keywords

def test_neutral_matcher_exclusion():
    match = match_tender_against_profile(
        tender_title="Electrical supply and gas installation",
        tender_description="Gas distribution lines",
        tender_cpvs=[],
        tender_region="Mazowieckie",
        profile_keywords=["water"],
        profile_exclusions=["gas"],
        profile_cpvs=[],
        profile_regions=[]
    )
    assert match.decision == "REJECT"
    assert match.score == 0.0
    assert "gas" in match.exclusion_triggers

def test_import_pipeline_deduplication(db_session):
    tenant = Tenant(name="Test Tenant")
    db_session.add(tenant)
    db_session.commit()

    raw_notice = {
        "objectId": "obj-123",
        "bzpNumber": "2025/BZP 0001",
        "tenderId": "tender-1",
        "orderObject": "Water supply construction",
        "organizationName": "Test Buyer"
    }

    # First import
    stats1 = import_notices(db_session, tenant.id, [raw_notice])
    assert stats1["created_tenders"] == 1
    assert stats1["created_notices"] == 1

    # Second import with identical payload
    stats2 = import_notices(db_session, tenant.id, [raw_notice])
    assert stats2["created_tenders"] == 0
    assert stats2["created_notices"] == 0
    assert stats2["skipped_notices"] == 1

def test_dry_run_read_only(db_session, monkeypatch):
    monkeypatch.setattr(settings, "IMPORT_DRY_RUN_ENABLED", True)

    def mock_fetch_page(**kwargs):
        return {
            "items": [{
                "objectId": "dry-123",
                "bzpNumber": "2025/BZP 9999",
                "tenderId": "tender-999",
                "orderObject": "Dry run water project"
            }]
        }

    res = execute_bzp_dry_run(
        db=db_session,
        max_pages=1,
        page_size=10,
        fetch_fn=mock_fetch_page,
        environment="test"
    )
    assert res["dry_run"] is True
    assert res["summary"]["total_items"] == 1
    assert res["summary"]["classifications"]["NEW"] == 1

    # Ensure no records were added to DB
    tenders_count = db_session.query(Tender).count()
    notices_count = db_session.query(TenderNotice).count()
    assert tenders_count == 0
    assert notices_count == 0
