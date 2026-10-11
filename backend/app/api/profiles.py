import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user, verify_profile_access
from app.models import User, ContractorProfile
from app.schemas import ProfileCreate, ProfileUpdate, ProfileResponse
from app.services.profile_service import create_contractor_profile, activate_contractor_profile

router = APIRouter()

@router.get("", response_model=List[ProfileResponse])
def list_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(ContractorProfile).filter(
        ContractorProfile.tenant_id == current_user.tenant_id,
        ContractorProfile.status != "archived"
    ).all()

@router.post("", response_model=ProfileResponse)
def create_profile(
    profile_in: ProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return create_contractor_profile(
        db=db,
        tenant_id=current_user.tenant_id,
        name=profile_in.name,
        description=profile_in.description,
        status_str=profile_in.status,
        competencies=profile_in.competencies,
        keywords=profile_in.keywords,
        exclusions=profile_in.exclusions,
        regions=profile_in.regions,
        cpv_codes=profile_in.cpv_codes,
        scoring_rules=profile_in.scoring_rules,
        is_default=profile_in.is_default
    )

@router.get("/{profile_id}", response_model=ProfileResponse)
def get_profile(
    profile_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return verify_profile_access(profile_id, db, current_user)

@router.patch("/{profile_id}", response_model=ProfileResponse)
def update_profile(
    profile_id: uuid.UUID,
    profile_in: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = verify_profile_access(profile_id, db, current_user)

    update_data = profile_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile

@router.delete("/{profile_id}")
def archive_profile(
    profile_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = verify_profile_access(profile_id, db, current_user)
    profile.status = "archived"
    db.commit()
    return {"message": "Profile archived"}

@router.post("/{profile_id}/activate", response_model=ProfileResponse)
def activate_profile(
    profile_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return activate_contractor_profile(db, profile_id, current_user)
