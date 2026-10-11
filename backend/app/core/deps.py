import uuid
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import User, Tenant, ContractorProfile

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
    x_company_id: Optional[str] = Header(None, alias="X-Company-ID")
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    # If X-Company-ID header is supplied, verify that the user belongs to that tenant or is system admin
    if x_company_id:
        try:
            target_tenant_id = uuid.UUID(x_company_id)
            if user.tenant_id != target_tenant_id and not user.is_admin:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to requested tenant denied")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid X-Company-ID format")

    return user

def get_current_active_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="The user doesn't have enough privileges"
        )
    return current_user

def verify_tenant_access(
    tenant_id: uuid.UUID,
    current_user: User
) -> None:
    if current_user.tenant_id != tenant_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to tenant resources forbidden"
        )

def verify_profile_access(
    profile_id: uuid.UUID,
    db: Session,
    current_user: User
) -> ContractorProfile:
    profile = db.query(ContractorProfile).filter(ContractorProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contractor profile not found")
    if profile.tenant_id != current_user.tenant_id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to contractor profile forbidden")
    return profile
