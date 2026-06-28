"""Auth and subscription schemas."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr


class RegisterIn(BaseModel):
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_admin: bool


class SubscriptionIn(BaseModel):
    service_id: uuid.UUID
    clinic_id: uuid.UUID | None = None
    target_price_kzt: float | None = None


class SubscriptionOut(BaseModel):
    id: uuid.UUID
    service_id: uuid.UUID
    clinic_id: uuid.UUID | None = None
    target_price_kzt: float | None = None
