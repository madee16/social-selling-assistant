import uuid

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(min_length=6, max_length=128)
    company_name: str = Field(max_length=255)
    phone: str | None = Field(None, max_length=50)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(max_length=255)


class ResetPasswordRequest(BaseModel):
    token: str = Field(max_length=255)
    new_password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    company_name: str
    company_logo_url: str | None = None
    phone: str | None = None
    preferred_language: str = "fr"
    currency: str = "TND"
    notifications_enabled: bool = True
    ai_custom_instructions: str | None = None

    model_config = {"from_attributes": True}
