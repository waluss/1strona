import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user, get_current_active_admin, verify_tenant_access
from app.core.security import get_password_hash
from app.models import Tenant, User
from app.schemas import TenantCreate, TenantResponse, UserCreate, UserResponse

router = APIRouter()

@router.post("", response_model=TenantResponse)
def create_tenant(
    tenant_in: TenantCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin)
):
    tenant = Tenant(name=tenant_in.name, is_active=True)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant

@router.get("", response_model=List[TenantResponse])
def list_tenants(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.is_admin:
        return db.query(Tenant).all()
    return db.query(Tenant).filter(Tenant.id == current_user.tenant_id).all()

@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_tenant_access(tenant_id, current_user)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant

@router.post("/{tenant_id}/users", response_model=UserResponse)
def create_tenant_user(
    tenant_id: uuid.UUID,
    user_in: UserCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin)
):
    verify_tenant_access(tenant_id, admin_user)

    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    user = User(
        tenant_id=tenant_id,
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
        is_admin=user_in.is_admin,
        must_change_password=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.get("/{tenant_id}/users", response_model=List[UserResponse])
def list_tenant_users(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_tenant_access(tenant_id, current_user)
    return db.query(User).filter(User.tenant_id == tenant_id).all()
