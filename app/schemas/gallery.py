"""Esquemas de categorías y archivos de la galería."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
