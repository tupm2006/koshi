import os
import json
import base64
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.entities import User, RoleEnum
from app.schemas.auth import UserRegister, UserLogin, GoogleAuthRequest, UserOut, Token
from app.security import verify_password, get_password_hash, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register_user(req: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )
    
    hashed = get_password_hash(req.password)
    user = User(
        email=req.email,
        hashed_password=hashed,
        full_name=req.full_name,
        role=req.role or RoleEnum.MEMBER,
        skills=req.skills or "general"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return Token(access_token=access_token, token_type="bearer", user=user)

@router.post("/login", response_model=Token)
def login_user(req: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.hashed_password or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return Token(access_token=access_token, token_type="bearer", user=user)

@router.post("/google", response_model=Token)
def google_auth(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Verify Google OAuth ID Token strictly.
    Eliminated all unverified JWT fallback decoding for P0 security compliance.
    """
    email = None
    full_name = None
    google_id = None
    avatar_url = None

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        id_info = id_token.verify_oauth2_token(req.credential, google_requests.Request())
        email = id_info.get("email")
        full_name = id_info.get("name") or id_info.get("given_name") or (email.split("@")[0] if email else "Google User")
        google_id = id_info.get("sub")
        avatar_url = id_info.get("picture")
    except Exception as e:
        # Mock token handling ONLY permitted in automated test suites
        is_test_env = bool(os.getenv("PYTEST_CURRENT_TEST")) or settings.ENVIRONMENT in ("test", "testing")
        if is_test_env and req.credential.startswith("mock_google_token_"):
            email = req.credential.replace("mock_google_token_", "")
            full_name = "Google Test User"
            google_id = f"mock_gid_{email}"
            avatar_url = "https://lh3.googleusercontent.com/a/default-user"
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Google ID token signature verification failed: {str(e)}"
            )

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google ID token missing verified email address"
        )

    # Check if user exists by google_id or email
    user = db.query(User).filter((User.google_id == google_id) | (User.email == email)).first()

    if user:
        if not user.google_id and google_id:
            user.google_id = google_id
        if avatar_url:
            user.avatar_url = avatar_url
        if not user.full_name and full_name:
            user.full_name = full_name
        db.commit()
        db.refresh(user)
    else:
        total_users = db.query(User).count()
        role = RoleEnum.PM if total_users == 0 else RoleEnum.MEMBER
        user = User(
            email=email,
            full_name=full_name or email.split("@")[0],
            google_id=google_id,
            avatar_url=avatar_url,
            role=role,
            skills="frontend,backend,general"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return Token(access_token=access_token, token_type="bearer", user=user)

@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user
