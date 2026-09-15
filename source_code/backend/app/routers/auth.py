import os
import json
import base64
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

try:
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
except ImportError:
    id_token = None
    google_requests = None

from app.database import get_db
from app.models.entities import User, RoleEnum, ProjectMember, ProjectMemberRoleEnum, Project
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    GoogleAuthRequest,
    TokenResponse,
    UserOut
)
from app.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)
from app.config import settings

router = APIRouter(prefix="", tags=["Authentication"])

@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@router.post("/api/v1/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    email_clean = req.email.strip().lower()
    existing = db.query(User).filter(User.email == email_clean).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    user_role = req.role if getattr(req, "role", None) else (RoleEnum.PM if ("tupm" in email_clean or "pm" in email_clean) else RoleEnum.MEMBER)
    user = User(
        email=email_clean,
        hashed_password=get_password_hash(req.password),
        full_name=req.full_name.strip(),
        role=user_role,
        skills=getattr(req, "skills", "") or ""
    )
    db.add(user)
    db.commit()
    db.refresh(user)



    role_val = user.role.value if hasattr(user.role, 'value') else str(user.role)
    token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": role_val})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/auth/login", response_model=TokenResponse)
@router.post("/api/v1/auth/login", response_model=TokenResponse)
def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    email_clean = req.email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()
    if not user or not user.hashed_password or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    role_val = user.role.value if hasattr(user.role, 'value') else str(user.role)
    token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": role_val})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

def _decode_unverified_payload(credential: str):
    try:
        if credential.startswith("mock_google_token_"):
            mock_email = credential.replace("mock_google_token_", "").strip().lower()
            return {
                "email": mock_email,
                "name": mock_email.split("@")[0].capitalize(),
                "sub": f"mock_gid_{mock_email}",
                "picture": "https://lh3.googleusercontent.com/a/default-user"
            }
        elif "." in credential:
            parts = credential.split(".")
            if len(parts) >= 2:
                payload_b64 = parts[1]
                payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
                decoded_bytes = base64.urlsafe_b64decode(payload_b64)
                return json.loads(decoded_bytes.decode("utf-8"))
        elif "mock" in credential or "demo" in credential:
            return {
                "email": "demo.user@ictu.edu.vn",
                "name": "Demo User",
                "sub": "mock_gid_demo",
                "picture": "https://lh3.googleusercontent.com/a/default-user"
            }
        else:
            payload_b64 = credential + "=" * ((4 - len(credential) % 4) % 4)
            decoded_bytes = base64.urlsafe_b64decode(payload_b64)
            data = json.loads(decoded_bytes.decode("utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        return None
    return None

@router.post("/auth/google", response_model=TokenResponse)
@router.post("/api/v1/auth/google", response_model=TokenResponse)
def google_auth(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    credential = req.credential
    id_info = None

    if id_token is not None and google_requests is not None:
        try:
            id_info = id_token.verify_oauth2_token(
                credential,
                google_requests.Request()
            )
        except Exception as verify_err:
            if settings.ALLOW_UNVERIFIED_GOOGLE_TOKENS:
                id_info = _decode_unverified_payload(credential)
                if not id_info:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Google token verification failed and fallback decoding failed: {str(verify_err)}"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Google ID token signature verification failed: {str(verify_err)}"
                )
    else:
        if settings.ALLOW_UNVERIFIED_GOOGLE_TOKENS:
            id_info = _decode_unverified_payload(credential)
            if not id_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google auth library not available and invalid payload"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google auth library not available on server"
            )

    email = (id_info.get("email") or "").strip().lower()
    google_id = id_info.get("sub") or id_info.get("id") or id_info.get("google_id")
    if not email and not google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token payload does not contain a valid email or user identifier."
        )

    # Upsert user by google_id or email
    user = None
    if google_id:
        user = db.query(User).filter(User.google_id == google_id).first()
    if not user and email:
        user = db.query(User).filter(User.email == email).first()

    name = id_info.get("name") or id_info.get("full_name") or (email.split("@")[0].capitalize() if email else "Google User")
    picture = id_info.get("picture") or id_info.get("avatar_url") or ("https://api.dicebear.com/7.x/bottts/svg?seed=" + email if email else None)

    if not user:
        is_pm = "tupm" in email or "pm@" in email
        user = User(
            email=email or f"{google_id}@google.user",
            hashed_password="",
            full_name=name,
            google_id=google_id,
            avatar_url=picture,
            avatar_file=None,
            role=RoleEnum.PM if is_pm else RoleEnum.MEMBER,
            skills=""
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Auto-join default Project #1 if exists
        default_proj = db.query(Project).filter(Project.id == 1).first()
        if default_proj:
            membership = db.query(ProjectMember).filter(
                ProjectMember.project_id == 1,
                ProjectMember.user_id == user.id
            ).first()
            if not membership:
                membership = ProjectMember(
                    project_id=1,
                    user_id=user.id,
                    role=ProjectMemberRoleEnum.PM if user.role == RoleEnum.PM else ProjectMemberRoleEnum.MEMBER
                )
                db.add(membership)
                db.commit()
    else:
        updated = False
        if google_id and not user.google_id:
            user.google_id = google_id
            updated = True
        if picture and not user.avatar_url:
            user.avatar_url = picture
            updated = True
        if name and not user.full_name:
            user.full_name = name
            updated = True
        if updated:
            db.commit()
            db.refresh(user)

    role_val = user.role.value if hasattr(user.role, 'value') else str(user.role)
    token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": role_val})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/auth/me", response_model=UserOut)
@router.get("/api/v1/auth/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
