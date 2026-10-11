import hashlib
import json
import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import (
    Tenant, Tender, TenderNotice, TenderNoticeRevision, ImportRun, ContractorProfile
)
from app.importers.bzp_client import fetch_all_bzp_notices
from app.importers.bzp_dto import BzpNoticeDTO
from app.importers.bzp_normalizer import normalize_bzp_notice, NormalizedNoticeEvent
from app.scoring.neutral_scorer import score_tender_for_profile

logger = logging.getLogger(__name__)

def _canonical_hash(raw_json: Dict[str, Any]) -> str:
    """Computes a canonical SHA256 hash of JSON payload for change detection."""
    canonical_bytes = json.dumps(raw_json, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(canonical_bytes).hexdigest()

def _classify_notice(
    db: Session,
    normalized: NormalizedNoticeEvent
) -> tuple[str, Optional[TenderNotice]]:
    """Classifies a notice as NEW, SKIP (identical), or CHANGED."""
    existing_notice = db.query(TenderNotice).filter(
        TenderNotice.source_system == normalized.source_system,
        TenderNotice.notice_id == normalized.notice_id
    ).first()

    if not existing_notice:
        return "NEW", None

    current_hash = _canonical_hash(normalized.raw_json)
    if existing_notice.payload_hash == current_hash:
        return "SKIP", existing_notice
    else:
        return "CHANGED", existing_notice

def _should_update_tender_view(
    tender: Tender,
    normalized: NormalizedNoticeEvent
) -> bool:
    """Determines whether the tender view should be updated based on notice publication date."""
    if not tender.source_published_at or not normalized.published_at:
        return True
    return normalized.published_at >= tender.source_published_at

def import_notices(
    db: Session,
    tenant_id: uuid.UUID,
    raw_notices: List[Dict[str, Any]],
    import_run_id: Optional[uuid.UUID] = None
) -> Dict[str, Any]:
    stats = {
        "total_fetched": len(raw_notices),
        "created_tenders": 0,
        "updated_tenders": 0,
        "created_notices": 0,
        "updated_notices": 0,
        "skipped_notices": 0,
        "errors": 0
    }

    import_run = None
    if import_run_id:
        import_run = db.query(ImportRun).filter(ImportRun.id == import_run_id).first()
        if import_run:
            import_run.status = "RUNNING"
            db.commit()

    active_profiles = db.query(ContractorProfile).filter(
        ContractorProfile.tenant_id == tenant_id,
        ContractorProfile.status == "active"
    ).all()

    for item in raw_notices:
        savepoint = db.begin_nested()
        try:
            dto = BzpNoticeDTO.model_validate(item)
            normalized = normalize_bzp_notice(dto)

            # 1. Process Tender (Deduplicate by (source_system, source_proceeding_id))
            tender = db.query(Tender).filter(
                Tender.tenant_id == tenant_id,
                Tender.source_system == normalized.source_system,
                Tender.source_proceeding_id == normalized.source_proceeding_id
            ).first()

            if not tender:
                tender = Tender(
                    tenant_id=tenant_id,
                    source_system=normalized.source_system,
                    source_proceeding_id=normalized.source_proceeding_id,
                    title=normalized.title,
                    buyer_name=normalized.buyer_name,
                    buyer_nip=normalized.buyer_nip,
                    submission_deadline_at=normalized.submission_deadline_at,
                    location_voivodeship=normalized.location_voivodeship,
                    cpv_codes=normalized.cpv_codes,
                    estimated_value_net=normalized.estimated_value_net,
                    raw_notice=normalized.raw_json,
                    source_published_at=normalized.published_at,
                    requires_scoring=True
                )
                db.add(tender)
                db.flush()
                stats["created_tenders"] += 1
            else:
                if _should_update_tender_view(tender, normalized):
                    tender.title = normalized.title
                    if normalized.buyer_name:
                        tender.buyer_name = normalized.buyer_name
                    if normalized.buyer_nip:
                        tender.buyer_nip = normalized.buyer_nip
                    if normalized.submission_deadline_at:
                        tender.submission_deadline_at = normalized.submission_deadline_at
                    if normalized.location_voivodeship:
                        tender.location_voivodeship = normalized.location_voivodeship
                    if normalized.cpv_codes:
                        tender.cpv_codes = normalized.cpv_codes
                    if normalized.estimated_value_net:
                        tender.estimated_value_net = normalized.estimated_value_net
                    tender.raw_notice = normalized.raw_json
                    tender.source_published_at = normalized.published_at
                    tender.requires_scoring = True
                    stats["updated_tenders"] += 1

            # 2. Process Notice (Deduplicate by (source_system, notice_id))
            classification, existing_notice = _classify_notice(db, normalized)
            new_hash = _canonical_hash(normalized.raw_json)

            if classification == "NEW":
                notice = TenderNotice(
                    tender_id=tender.id,
                    source_system=normalized.source_system,
                    notice_id=normalized.notice_id,
                    notice_number=normalized.notice_number,
                    notice_kind=normalized.notice_kind,
                    raw_json=normalized.raw_json,
                    payload_hash=new_hash,
                    published_at=normalized.published_at,
                    fetched_at=datetime.utcnow()
                )
                db.add(notice)
                db.flush()
                tender.current_notice_id = notice.id
                stats["created_notices"] += 1

            elif classification == "CHANGED":
                # Create revision for changed notice
                revision = TenderNoticeRevision(
                    tender_notice_id=existing_notice.id,
                    previous_payload_hash=existing_notice.payload_hash,
                    previous_raw_json=existing_notice.raw_json,
                    changed_at=datetime.utcnow(),
                    change_reason="Updated payload received during import"
                )
                db.add(revision)

                existing_notice.raw_json = normalized.raw_json
                existing_notice.payload_hash = new_hash
                existing_notice.published_at = normalized.published_at
                existing_notice.is_delta = True
                existing_notice.fetched_at = datetime.utcnow()
                tender.current_notice_id = existing_notice.id
                stats["updated_notices"] += 1

            else:  # SKIP
                stats["skipped_notices"] += 1

            # 3. Trigger production scoring for active profiles if required
            if tender and tender.requires_scoring and active_profiles:
                for profile in active_profiles:
                    score_tender_for_profile(db, tender, profile, persist=True)

            savepoint.commit()

        except Exception as e:
            savepoint.rollback()
            logger.error(f"Error importing item: {e}")
            stats["errors"] += 1

    db.commit()

    if import_run:
        import_run.status = "COMPLETED" if stats["errors"] == 0 else "FAILED"
        import_run.finished_at = datetime.utcnow()
        import_run.statistics = stats
        db.commit()

    return stats
