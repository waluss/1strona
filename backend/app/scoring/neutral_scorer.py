import uuid
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import Tender, ContractorProfile, TenderScore
from app.scoring.neutral_matcher import match_tender_against_profile, MatchDecision

logger = logging.getLogger(__name__)

def score_tender_for_profile(
    db: Session,
    tender: Tender,
    profile: ContractorProfile,
    persist: bool = True
) -> Dict[str, Any]:
    if profile.status == "candidate":
        # candidate profiles must not be used by production scoring
        if persist:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Candidate profile cannot be used for production scoring")

    match_result = match_tender_against_profile(
        tender_title=tender.title,
        tender_description=str(tender.raw_notice.get("orderObject", "")) if tender.raw_notice else "",
        tender_cpvs=tender.cpv_codes or [],
        tender_region=tender.location_voivodeship or "",
        profile_keywords=profile.keywords or [],
        profile_exclusions=profile.exclusions or [],
        profile_cpvs=profile.cpv_codes or [],
        profile_regions=profile.regions or []
    )

    breakdown = {
        "decision": match_result.decision,
        "score": match_result.score,
        "reasons": match_result.reasons,
        "matched_keywords": match_result.matched_keywords,
        "matched_cpvs": match_result.matched_cpvs,
        "matched_regions": match_result.matched_regions,
        "exclusion_triggers": match_result.exclusion_triggers,
        "profile_name": profile.name,
        "profile_id": str(profile.id)
    }

    if persist:
        # Check if score already exists for this tender and profile
        existing_score = db.query(TenderScore).filter(
            TenderScore.tender_id == tender.id,
            TenderScore.contractor_profile_id == profile.id
        ).first()

        if existing_score:
            existing_score.score = match_result.score
            existing_score.decision = match_result.decision
            existing_score.breakdown = breakdown
            score_record = existing_score
        else:
            score_record = TenderScore(
                tender_id=tender.id,
                contractor_profile_id=profile.id,
                score=match_result.score,
                decision=match_result.decision,
                breakdown=breakdown,
                scoring_version="1.0"
            )
            db.add(score_record)

        db.commit()
        db.refresh(score_record)

    return breakdown
