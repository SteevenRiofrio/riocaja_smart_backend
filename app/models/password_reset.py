# -*- coding: utf-8 -*-
# app/models/password_reset.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class PasswordResetRequest(BaseModel):
    email: EmailStr

class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8)

class PasswordResetResponse(BaseModel):
    success: bool
    message: str
    reset_id: Optional[str] = None

class ResetStatsResponse(BaseModel):
    email: str
    has_active_request: bool
    attempts_remaining: int
    expires_at: Optional[datetime] = None
    last_request_at: Optional[datetime] = None