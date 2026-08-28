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

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    user = User(
        email=req.email.lower(),
        hashed_password=get_password_hash(req.password),
        full_name=req.full_name,
        role=RoleEnum.MEMBER
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Auto-assign new users to default project #1 as MEMBER if project exists
    default_proj = db.query(Project).filter(Project.id == 1).first()
    if default_proj:
        member_record = db.query(ProjectMember).filter(
            ProjectMember.project_id == 1,
            ProjectMember.user_id == user.id
        ).first()
        if not member_record:
            member_record = ProjectMember(
                project_id=1,
                user_id=user.id,
                role=ProjectMemberRoleEnum.MEMBER
            )
            db.add(member_record)
            db.commit()

    token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role.value if hasattr(user.role, 'value') else str(user.role)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/login", response_model=TokenResponse)
def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower()).first()
    if not user or not user.hashed_password or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role.value if hasattr(user.role, 'value') else str(user.role)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/google", response_model=TokenResponse)
def google_auth(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    credential = req.credential
    id_info = None

    # Controlled Demo / Academic Mock Token Support
    if credential.startswith("mock_google_token_") or credential.endswith(".mock_signature") or "mock_google_token" in credential:
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
                    "picture": "https://api.dicebear.com/7.x/bottts/svg?seed=demo"
                }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid demo token payload: {str(e)}"
            )
    else:
        # Authentic Google JWKS Public Key Verification
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

    email = id_info.get("email", "").lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token payload does not contain an email address."
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            hashed_password="",
            full_name=id_info.get("name", email.split("@")[0]),
            google_id=id_info.get("sub"),
            avatar_url=id_info.get("picture"),
            role=RoleEnum.PM if "tupm" in email else RoleEnum.MEMBER
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Automatically join default project #1 if project exists
        default_proj = db.query(Project).filter(Project.id == 1).first()
        if default_proj:
            member_record = db.query(ProjectMember).filter(
                ProjectMember.project_id == 1,
                ProjectMember.user_id == user.id
            ).first()
            if not member_record:
                member_record = ProjectMember(
                    project_id=1,
                    user_id=user.id,
                    role=ProjectMemberRoleEnum.PM if user.role == RoleEnum.PM else ProjectMemberRoleEnum.MEMBER
                )
                db.add(member_record)
                db.commit()
    else:
        if id_info.get("picture") and not user.avatar_url:
            user.avatar_url = id_info.get("picture")
            db.commit()
            db.refresh(user)

    token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role.value if hasattr(user.role, 'value') else str(user.role)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
