from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.entities import RoleEnum

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Optional[RoleEnum] = RoleEnum.MEMBER
    skills: Optional[str] = "python,svelte,sql"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: RoleEnum
    skills: str
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class TokenPayload(BaseModel):
    sub: str
    role: str
