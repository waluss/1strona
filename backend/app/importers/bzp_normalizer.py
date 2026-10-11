from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from app.importers.bzp_dto import BzpNoticeDTO

MISSING = "MISSING"

class NormalizedNoticeEvent(BaseModel):
    source_system: str = "BZP"
    source_proceeding_id: str
    notice_id: str
    notice_number: Optional[str] = None
    notice_kind: Optional[str] = None
    raw_json: Dict[str, Any]
    published_at: Optional[datetime] = None
    title: str
    buyer_name: Optional[str] = None
    buyer_nip: Optional[str] = None
    submission_deadline_at: Optional[datetime] = None
    cpv_codes: List[str] = []
    location_voivodeship: Optional[str] = None
    estimated_value_net: Optional[float] = None


def parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str or dt_str == MISSING:
        return None
    try:
        # Handle trailing Z or offsets
        clean_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_str)
    except Exception:
        return None


def normalize_bzp_notice(dto: BzpNoticeDTO) -> NormalizedNoticeEvent:
    raw_json = dto.model_dump()

    # Determine notice ID and proceeding ID
    notice_id = dto.objectId or dto.bzpNumber or dto.noticeNumber or MISSING
    source_proceeding_id = dto.tenderId or dto.bzpNumber or notice_id

    # Title / orderObject
    title = dto.orderObject or "Brak tytułu ogłoszenia"

    # Buyer details
    buyer_name = dto.organizationName or None
    buyer_nip = dto.organizationNationalId or None

    # Dates
    published_at = parse_iso_datetime(dto.publicationDate)
    submission_deadline_at = parse_iso_datetime(dto.submittingOffersDate)

    # CPV codes
    cpv_list = []
    if dto.cpvCode:
        cpv_list.append(dto.cpvCode)
    if dto.cpvCodes:
        for code in dto.cpvCodes:
            if code and code not in cpv_list:
                cpv_list.append(code)

    # Location
    location_voivodeship = dto.organizationProvince or None

    # Estimated value
    estimated_value_net = dto.estimatedValue or None

    return NormalizedNoticeEvent(
        source_system="BZP",
        source_proceeding_id=source_proceeding_id,
        notice_id=notice_id,
        notice_number=dto.noticeNumber or dto.bzpNumber,
        notice_kind=dto.noticeType or dto.orderType,
        raw_json=raw_json,
        published_at=published_at,
        title=title,
        buyer_name=buyer_name,
        buyer_nip=buyer_nip,
        submission_deadline_at=submission_deadline_at,
        cpv_codes=cpv_list,
        location_voivodeship=location_voivodeship,
        estimated_value_net=estimated_value_net
    )
