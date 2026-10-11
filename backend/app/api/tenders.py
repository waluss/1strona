import uuid
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models import User, Tender, TenderNotice, TenderScore, ContractorProfile
from app.schemas import TenderResponse, TenderNoticeResponse, ScoreResponse
from app.scoring.neutral_scorer import score_tender_for_profile

router = APIRouter()

@router.get("", response_model=List[TenderResponse])
def list_tenders(
    published_from: Optional[datetime] = None,
    published_to: Optional[datetime] = None,
    deadline_from: Optional[datetime] = None,
    deadline_to: Optional[datetime] = None,
    voivodeship: Optional[str] = None,
    cpv_code: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    profile_id: Optional[uuid.UUID] = None,
    match_result: Optional[str] = None,  # MATCH, REJECT, MANUAL_REVIEW
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Tender).filter(Tender.tenant_id == current_user.tenant_id)

    if published_from:
        query = query.filter(Tender.source_published_at >= published_from)
    if published_to:
        query = query.filter(Tender.source_published_at <= published_to)
    if deadline_from:
        query = query.filter(Tender.submission_deadline_at >= deadline_from)
    if deadline_to:
        query = query.filter(Tender.submission_deadline_at <= deadline_to)
    if voivodeship:
        query = query.filter(Tender.location_voivodeship.ilike(f"%{voivodeship}%"))
    if cpv_code:
        query = query.filter(Tender.cpv_codes.contains([cpv_code]))
    if status_filter:
        query = query.filter(Tender.status == status_filter)
    if search:
        query = query.filter(
            or_(
                Tender.title.ilike(f"%{search}%"),
                Tender.buyer_name.ilike(f"%{search}%")
            )
        )

    if profile_id or match_result:
        query = query.join(TenderScore, TenderScore.tender_id == Tender.id)
        if profile_id:
            query = query.filter(TenderScore.contractor_profile_id == profile_id)
        if match_result:
            query = query.filter(TenderScore.decision == match_result)

    return query.order_by(Tender.source_published_at.desc().nullslast()).offset(skip).limit(limit).all()


@router.get("/{tender_id}", response_model=TenderResponse)
def get_tender(
    tender_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tender = db.query(Tender).filter(Tender.id == tender_id, Tender.tenant_id == current_user.tenant_id).first()
    if not tender:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")
    return tender


@router.get("/{tender_id}/notices", response_model=List[TenderNoticeResponse])
def get_tender_notices(
    tender_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tender = db.query(Tender).filter(Tender.id == tender_id, Tender.tenant_id == current_user.tenant_id).first()
    if not tender:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")
    return db.query(TenderNotice).filter(TenderNotice.tender_id == tender_id).all()


@router.get("/{tender_id}/scores", response_model=List[ScoreResponse])
def get_tender_scores(
    tender_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tender = db.query(Tender).filter(Tender.id == tender_id, Tender.tenant_id == current_user.tenant_id).first()
    if not tender:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")
    return db.query(TenderScore).filter(TenderScore.tender_id == tender_id).all()


@router.get("/{tender_id}/profile-score")
def preview_tender_profile_score(
    tender_id: uuid.UUID,
    profile_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tender = db.query(Tender).filter(Tender.id == tender_id, Tender.tenant_id == current_user.tenant_id).first()
    if not tender:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")

    profile = db.query(ContractorProfile).filter(ContractorProfile.id == profile_id, ContractorProfile.tenant_id == current_user.tenant_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contractor profile not found")

    # In-memory preview score without persisting to tender_scores
    breakdown = score_tender_for_profile(db, tender, profile, persist=False)
    return {"preview_only": True, "breakdown": breakdown}
