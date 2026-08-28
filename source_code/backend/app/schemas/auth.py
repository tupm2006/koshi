from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.entities import RoleEnum

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Optional[RoleEnum] = RoleEnum.MEMBER
    skills: Optional[str] = ""

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleAuthRequest(BaseModel):
    credential: str

class UserUpdate(BaseModel):
    role: Optional[RoleEnum] = None
    skills: Optional[str] = None
    full_name: Optional[str] = None

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    google_id: Optional[str] = None
    avatar_url: Optional[str] = None
    role: RoleEnum
    skills: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserWithWIPOut(UserOut):
    active_tasks_count: int = 0
    wip_points: int = 0

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class TokenPayload(BaseModel):
    sub: str
    role: str

# Aliases for request and response models
UserRegisterRequest = UserRegister
UserLoginRequest = UserLogin
TokenResponse = Token
UserResponse = UserOut
