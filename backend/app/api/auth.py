from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.db.session import get_db
from app.core.config import settings
from app.core.security import (
    verify_password, get_password_hash, create_access_token, create_refresh_token
)
from app.core.deps import get_current_user
from app.models import User
from app.schemas import (
    LoginRequest, Token, RefreshTokenRequest, ChangePasswordRequest, UserResponse
)

router = APIRouter()

@router.post("/login", response_model=Token)
def login(login_req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == login_req.username).first()
    if not user or not verify_password(login_req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    access_token = create_access_token(user.id, user.tenant_id, user.is_admin)
    refresh_token = create_refresh_token(user.id, user.tenant_id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        must_change_password=user.must_change_password
    )

@router.post("/refresh", response_model=Token)
def refresh_token(req: RefreshTokenRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(req.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        token_type = payload.get("type")
        if not user_id or token_type != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    new_access_token = create_access_token(user.id, user.tenant_id, user.is_admin)
    new_refresh_token = create_refresh_token(user.id, user.tenant_id)

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        must_change_password=user.must_change_password
    )

@router.post("/logout")
def logout():
    return {"message": "Successfully logged out"}

@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password")

    current_user.hashed_password = get_password_hash(req.new_password)
    current_user.must_change_password = False
    db.commit()

    return {"message": "Password changed successfully"}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
