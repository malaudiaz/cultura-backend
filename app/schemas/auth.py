"""Esquemas para autenticación local y social."""

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.users import UserResponse


class LocalRegister(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        return value


class LocalLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class SocialToken(BaseModel):
    token: str = Field(min_length=20)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
