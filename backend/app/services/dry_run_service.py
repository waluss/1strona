import uuid
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.importers.bzp_client import fetch_bzp_notices_page, BZP_NOTICE_TYPES
from app.importers.bzp_dto import BzpNoticeDTO
from app.importers.bzp_normalizer import normalize_bzp_notice
from app.services.importer import _canonical_hash
from app.models import TenderNotice, Tender

logger = logging.getLogger(__name__)

NAMESPACE_DRY_RUN = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')

def _parse_and_validate_dates(date_from: Optional[str], date_to: Optional[str]):
    if not date_from or not date_to:
        return
    try:
        dt_from = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
        dt_to = datetime.fromisoformat(date_to.replace("Z", "+00:00"))

        if (dt_from.tzinfo is None) != (dt_to.tzinfo is None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dates must both be timezone-aware or both naive")

        if dt_from > dt_to:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="date_from must be <= date_to")
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid date format: {ve}")


def execute_bzp_dry_run(
    db: Session,
    notice_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    max_pages: int = 1,
    page_size: int = 50,
    fetch_fn: Optional[Callable[..., Any]] = None,
    environment: Optional[str] = None
) -> Dict[str, Any]:
    # Strict Environment Guard Check
    current_env = (environment or settings.ENVIRONMENT).lower()
    if current_env in ("production", "prod"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Dry run import disabled in production")

    if current_env not in ("local", "dev", "test"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unknown environment for dry run import")

    if not settings.IMPORT_DRY_RUN_ENABLED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dry run import feature is currently disabled")

    if notice_type and notice_type not in BZP_NOTICE_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid notice_type: {notice_type}")

    _parse_and_validate_dates(date_from, date_to)

    # Read active existing notices and tenders from DB using strictly SELECT queries
    existing_notices_db = db.query(TenderNotice).all()
    existing_tenders_db = db.query(Tender).all()

    notices_by_key = {f"{n.source_system}:{n.notice_id}": n for n in existing_notices_db}
    tenders_by_key = {f"{t.source_system}:{t.source_proceeding_id}": t for t in existing_tenders_db}

    classified_items = []
    summary_counts = {
        "total_items": 0,
        "classifications": {"NEW": 0, "SKIP": 0, "CHANGED": 0, "INTEGRITY_ERROR": 0, "UNCLASSIFIED": 0},
        "notice_actions": {"CREATE_NOTICE": 0, "UPDATE_NOTICE": 0, "SKIP_IDENTICAL": 0, "NEEDS_REVIEW": 0, "REJECTED": 0},
        "tender_actions": {"CREATE_TENDER": 0, "UPDATE_VIEW": 0, "KEEP_VIEW": 0, "NEEDS_REVIEW": 0, "NONE": 0}
    }

    pages_fetched = 0
    search_after = None
    pagination_status = "exhausted"

    while pages_fetched < max_pages:
        try:
            page_data = fetch_bzp_notices_page(
                notice_type=notice_type,
                publication_date_from=date_from,
                publication_date_to=date_to,
                search_after=search_after,
                page_size=page_size,
                fetch_fn=fetch_fn
            )
        except Exception as exc:
            logger.error(f"Error fetching page during dry-run: {exc}")
            break

        items = page_data if isinstance(page_data, list) else page_data.get("items", page_data.get("notices", []))

        if not items:
            if pages_fetched == 0:
                pagination_status = "empty_result"
            break

        pages_fetched += 1

        for raw_item in items:
            summary_counts["total_items"] += 1
            error_fields = []

            try:
                dto = BzpNoticeDTO.model_validate(raw_item)
                normalized = normalize_bzp_notice(dto)
            except Exception:
                summary_counts["classifications"]["UNCLASSIFIED"] += 1
                summary_counts["notice_actions"]["REJECTED"] += 1
                summary_counts["tender_actions"]["NONE"] += 1
                classified_items.append({
                    "raw_notice_id": raw_item.get("objectId") or "UNKNOWN",
                    "classification": "UNCLASSIFIED",
                    "classification_error": True,
                    "error_fields": ["payload_validation_error"],
                    "notice_action": "REJECTED",
                    "tender_action": "NONE",
                    "simulated_notice_id": str(uuid.uuid5(NAMESPACE_DRY_RUN, f"error-{summary_counts['total_items']}"))
                })
                continue

            simulated_notice_id = str(uuid.uuid5(NAMESPACE_DRY_RUN, f"{normalized.source_system}:{normalized.notice_id}"))
            notice_key = f"{normalized.source_system}:{normalized.notice_id}"
            tender_key = f"{normalized.source_system}:{normalized.source_proceeding_id}"

            payload_hash = _canonical_hash(normalized.raw_json)

            # Classify Notice
            existing_notice = notices_by_key.get(notice_key)
            if not existing_notice:
                classification = "NEW"
                notice_action = "CREATE_NOTICE"
            else:
                if existing_notice.payload_hash == payload_hash:
                    classification = "SKIP"
                    notice_action = "SKIP_IDENTICAL"
                else:
                    classification = "CHANGED"
                    notice_action = "UPDATE_NOTICE"

            # Classify Tender Action
            existing_tender = tenders_by_key.get(tender_key)
            if not existing_tender:
                tender_action = "CREATE_TENDER"
            else:
                if normalized.published_at and existing_tender.source_published_at and normalized.published_at >= existing_tender.source_published_at:
                    tender_action = "UPDATE_VIEW"
                else:
                    tender_action = "KEEP_VIEW"

            summary_counts["classifications"][classification] += 1
            summary_counts["notice_actions"][notice_action] += 1
            summary_counts["tender_actions"][tender_action] += 1

            classified_items.append({
                "source_system": normalized.source_system,
                "notice_id": normalized.notice_id,
                "source_proceeding_id": normalized.source_proceeding_id,
                "title": normalized.title,
                "classification": classification,
                "classification_error": False,
                "error_fields": error_fields,
                "notice_action": notice_action,
                "tender_action": tender_action,
                "simulated_notice_id": simulated_notice_id,
                "payload_hash": payload_hash
            })

        # Cursor pagination handling
        last_item = items[-1]
        next_cursor = last_item.get("objectId")
        if not next_cursor:
            pagination_status = "missing_cursor"
            break
        if next_cursor == search_after:
            pagination_status = "cursor_loop"
            break

        search_after = next_cursor

        if len(items) < page_size:
            pagination_status = "exhausted"
            break
        elif pages_fetched >= max_pages:
            pagination_status = "page_limit"

    return {
        "dry_run": True,
        "params": {
            "notice_type": notice_type,
            "date_from": date_from,
            "date_to": date_to,
            "max_pages": max_pages,
            "page_size": page_size
        },
        "pagination": {
            "pages_fetched": pages_fetched,
            "status": pagination_status
        },
        "summary": summary_counts,
        "items": classified_items
    }
