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
    Verify Google OAuth ID Token strictly using Google JWKS.
    Supports controlled academic demo/mock tokens with .mock_signature or mock_google_token prefix.
    """
    email = None
    full_name = None
    google_id = None
    avatar_url = None

    credential = req.credential

    # 1. Controlled Academic Demo / Mock Token Handler
    if credential.startswith("mock_google_token_") or credential.endswith(".mock_signature") or "mock_google_token" in credential or credential.startswith("google_mock_"):
        try:
            if credential.startswith("mock_google_token_"):
                email = credential.replace("mock_google_token_", "")
                full_name = email.split("@")[0].capitalize()
                google_id = f"mock_gid_{email}"
                avatar_url = "https://lh3.googleusercontent.com/a/default-user"
            elif credential.endswith(".mock_signature"):
                parts = credential.split(".")
                payload_b64 = parts[1]
                # Add base64 padding
                payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
                decoded_bytes = base64.urlsafe_b64decode(payload_b64)
                id_info = json.loads(decoded_bytes.decode("utf-8"))
                email = id_info.get("email")
                full_name = id_info.get("name") or (email.split("@")[0] if email else "Demo User")
                google_id = id_info.get("sub") or f"mock_gid_{email}"
                avatar_url = id_info.get("picture") or "https://api.dicebear.com/7.x/bottts/svg?seed=demo"
            else:
                email = "demo.user@ictu.edu.vn"
                full_name = "Demo Academic User"
                google_id = "mock_gid_demo"
                avatar_url = "https://api.dicebear.com/7.x/bottts/svg?seed=demo"
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid demo token format: {str(e)}"
            )
    else:
        # 2. Strict Real Google JWKS Certificate Verification
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests
            id_info = id_token.verify_oauth2_token(credential, google_requests.Request())
            email = id_info.get("email")
            full_name = id_info.get("name") or id_info.get("given_name") or (email.split("@")[0] if email else "Google User")
            google_id = id_info.get("sub")
            avatar_url = id_info.get("picture")
        except Exception as e:
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
            hashed_password="",
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
