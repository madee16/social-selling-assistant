from pydantic import BaseModel, Field


class ProfileUpdate(BaseModel):
    company_name: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    company_logo_url: str | None = Field(None, max_length=500)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class PreferencesUpdate(BaseModel):
    preferred_language: str | None = Field(None, max_length=10)
    currency: str | None = Field(None, max_length=3)
    notifications_enabled: bool | None = None
    ai_custom_instructions: str | None = Field(None, max_length=5000)
