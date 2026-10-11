import uuid
import threading
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import ContractorProfile, User

class ProfileRegistry:
    def __init__(self):
        self._lock = threading.RLock()
        self._cache = {}

    def get_profiles(self, tenant_id: uuid.UUID) -> List[dict]:
        with self._lock:
            return self._cache.get(tenant_id, [])

    def refresh_tenant(self, db: Session, tenant_id: uuid.UUID):
        with self._lock:
            profiles = db.query(ContractorProfile).filter(
                ContractorProfile.tenant_id == tenant_id,
                ContractorProfile.status != "archived"
            ).all()
            self._cache[tenant_id] = [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "status": p.status,
                    "keywords": p.keywords,
                    "cpv_codes": p.cpv_codes
                }
                for p in profiles
            ]

profile_registry = ProfileRegistry()

def create_contractor_profile(
    db: Session,
    tenant_id: uuid.UUID,
    name: str,
    description: Optional[str] = None,
    status_str: str = "candidate",
    competencies: List[str] = [],
    keywords: List[str] = [],
    exclusions: List[str] = [],
    regions: List[str] = [],
    cpv_codes: List[str] = [],
    scoring_rules: Dict[str, Any] = {},
    is_default: bool = False
) -> ContractorProfile:
    # Duplicate check within tenant
    existing = db.query(ContractorProfile).filter(
        ContractorProfile.tenant_id == tenant_id,
        ContractorProfile.name == name,
        ContractorProfile.status != "archived"
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contractor profile with this name already exists")

    if is_default:
        db.query(ContractorProfile).filter(
            ContractorProfile.tenant_id == tenant_id
        ).update({"is_default": False})

    profile = ContractorProfile(
        tenant_id=tenant_id,
        name=name,
        description=description,
        status=status_str,
        competencies=competencies,
        keywords=keywords,
        exclusions=exclusions,
        regions=regions,
        cpv_codes=cpv_codes,
        scoring_rules=scoring_rules,
        is_default=is_default
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    profile_registry.refresh_tenant(db, tenant_id)
    return profile

def activate_contractor_profile(
    db: Session,
    profile_id: uuid.UUID,
    user: User
) -> ContractorProfile:
    profile = db.query(ContractorProfile).filter(ContractorProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    if profile.tenant_id != user.tenant_id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    profile.status = "active"
    db.commit()
    db.refresh(profile)

    profile_registry.refresh_tenant(db, user.tenant_id)
    return profile
