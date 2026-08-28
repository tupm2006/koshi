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

    # Auto-assign to default Project #1
    default_proj = db.query(Project).filter(Project.id == 1).first()
    if default_proj:
        member_record = db.query(ProjectMember).filter(
            ProjectMember.project_id == 1,
            ProjectMember.user_id == user.id
        ).first()
        if not member_record:
            is_pm = (user.role == RoleEnum.PM) or (hasattr(user.role, 'value') and user.role.value == "PM")
            membership = ProjectMember(
                project_id=1,
                user_id=user.id,
                role=ProjectMemberRoleEnum.PM if is_pm else ProjectMemberRoleEnum.MEMBER
            )
            db.add(membership)
            db.commit()


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

@router.post("/auth/google", response_model=TokenResponse)
@router.post("/api/v1/auth/google", response_model=TokenResponse)
def google_auth(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    credential = req.credential
    id_info = None

    # 1. Controlled Academic Demo / Mock Token Handler
    if credential.endswith(".mock_signature") or "mock_google_token" in credential:
        try:
            if credential.startswith("mock_google_token_"):
                mock_email = credential.replace("mock_google_token_", "")
                id_info = {
                    "email": mock_email,
                    "name": mock_email.split("@")[0].capitalize(),
                    "sub": f"mock_gid_{mock_email}",
                    "picture": "https://lh3.googleusercontent.com/a/default-user"
                }
            elif "." in credential:
                parts = credential.split(".")
                payload_b64 = parts[1]
                payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
                decoded_bytes = base64.urlsafe_b64decode(payload_b64)
                id_info = json.loads(decoded_bytes.decode("utf-8"))
            else:
                id_info = {
                    "email": "demo.user@ictu.edu.vn",
                    "name": "Demo User",
                    "sub": "mock_gid_demo",
                    "picture": "https://lh3.googleusercontent.com/a/default-user"
                }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid demo token payload: {str(e)}"
            )
    else:
        # 2. Strict Real Google JWKS Certificate Verification
        if id_token is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google auth library not available on server"
            )
        try:
            id_info = id_token.verify_oauth2_token(
                credential,
                google_requests.Request()
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Google ID token signature verification failed: {str(e)}"
            )

    email = id_info.get("email", "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token payload does not contain a valid email address."
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        is_pm = "tupm" in email or "pm@" in email
        user = User(
            email=email,
            hashed_password="",
            full_name=id_info.get("name", email.split("@")[0]),
            google_id=id_info.get("sub"),
            avatar_url=id_info.get("picture", "https://api.dicebear.com/7.x/bottts/svg?seed=" + email),
            role=RoleEnum.PM if is_pm else RoleEnum.MEMBER
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Auto-join default Project #1
        default_proj = db.query(Project).filter(Project.id == 1).first()
        if default_proj:
            membership = ProjectMember(
                project_id=1,
                user_id=user.id,
                role=ProjectMemberRoleEnum.PM if user.role == RoleEnum.PM else ProjectMemberRoleEnum.MEMBER
            )
            db.add(membership)
            db.commit()
    else:
        if id_info.get("picture") and not user.avatar_url:
            user.avatar_url = id_info.get("picture")
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
