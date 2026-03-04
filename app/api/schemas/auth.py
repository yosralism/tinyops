from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: Literal["admin", "operator", "readonly"] = "operator"


class UserLogin(BaseModel):
    username: str
    password: str


class UserRead(BaseModel):
    model_config = {"from_attributes": True}
    
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: str | None = None
