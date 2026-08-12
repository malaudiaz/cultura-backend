import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.roles import Role


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


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    name: str
    role: Role
    created_at: datetime


class RoleUpdate(BaseModel):
    role: Role


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre de categoría no puede estar vacío")
        return value


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime


class GalleryImageResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    uploaded_by_id: uuid.UUID | None
    uploaded_by_name: str | None
    media_type: str
    duration_seconds: float | None
    url: str
    created_at: datetime


class GalleryImagePage(BaseModel):
    items: list[GalleryImageResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
