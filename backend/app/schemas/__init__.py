import uuid
from typing import Optional, List, Any, Dict
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict

# Auth schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    must_change_password: bool = False

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    username: str
    email: Optional[str] = None
    is_active: bool
    is_admin: bool
    must_change_password: bool
    created_at: datetime

# Tenant schemas
class TenantCreate(BaseModel):
    name: str

class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    is_active: bool
    created_at: datetime

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    is_admin: bool = False

# Profile schemas
class ProfileCreate(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "candidate"
    competencies: List[str] = []
    keywords: List[str] = []
    exclusions: List[str] = []
    regions: List[str] = []
    cpv_codes: List[str] = []
    scoring_rules: Dict[str, Any] = {}
    is_default: bool = False

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    competencies: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    exclusions: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    cpv_codes: Optional[List[str]] = None
    scoring_rules: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None

class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: Optional[str] = None
    status: str
    competencies: List[str]
    keywords: List[str]
    exclusions: List[str]
    regions: List[str]
    cpv_codes: List[str]
    scoring_rules: Dict[str, Any]
    is_default: bool
    created_at: datetime

# Tender schemas
class TenderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    source_system: str
    source_proceeding_id: str
    title: str
    buyer_name: Optional[str] = None
    buyer_nip: Optional[str] = None
    status: Optional[str] = None
    submission_deadline_at: Optional[datetime] = None
    location_voivodeship: Optional[str] = None
    cpv_codes: List[str]
    estimated_value_net: Optional[float] = None
    raw_notice: Optional[Dict[str, Any]] = None
    source_published_at: Optional[datetime] = None
    requires_scoring: bool
    created_at: datetime

class TenderNoticeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tender_id: uuid.UUID
    source_system: str
    notice_id: str
    notice_number: Optional[str] = None
    notice_kind: Optional[str] = None
    raw_json: Dict[str, Any]
    payload_hash: str
    published_at: Optional[datetime] = None
    fetched_at: datetime
    is_delta: bool

class ScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tender_id: uuid.UUID
    contractor_profile_id: uuid.UUID
    score: float
    decision: str
    breakdown: Dict[str, Any]
    created_at: datetime
