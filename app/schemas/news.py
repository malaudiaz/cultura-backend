"""Esquemas de lectura y escritura para noticias."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre no puede estar vacío")
        return value


class TagResponse(TagCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class TagUpdate(TagCreate):
    pass


class NewsSectionInput(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    image: str | None = Field(default=None, max_length=255)
    image_thumbnail: str | None = Field(default=None, max_length=255)
    content: str | None = None
    title_format: str | None = Field(default=None, max_length=50)
    element_order: list[str] | None = None
    position: int = Field(default=0, ge=0)


class NewsSectionCreate(NewsSectionInput):
    pass


class NewsSectionUpdate(NewsSectionInput):
    pass


class NewsSectionResponse(NewsSectionInput):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    news_id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None


class NewsCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    category_id: uuid.UUID
    summary: str | None = None
    image: str | None = Field(default=None, max_length=255)
    image_thumbnail: str | None = Field(default=None, max_length=255)
    featured: bool = False
    publication_date: date | None = None
    notes: str | None = None
    sections: list[NewsSectionCreate] = Field(default_factory=list)
    tag_ids: list[uuid.UUID] = Field(default_factory=list)


class NewsUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    category_id: uuid.UUID | None = None
    summary: str | None = None
    image: str | None = Field(default=None, max_length=255)
    image_thumbnail: str | None = Field(default=None, max_length=255)
    featured: bool | None = None
    publication_date: date | None = None
    notes: str | None = None
    tag_ids: list[uuid.UUID] | None = None


class NewsReview(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    notes: str | None = None


class NewsPublish(BaseModel):
    publication_date: date | None = None
    notes: str | None = None


class NewsRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    news_id: uuid.UUID
    editor_id: uuid.UUID
    action: str
    notes: str | None
    created_at: datetime


class NewsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    category_id: uuid.UUID
    status: str
    summary: str | None
    image: str | None
    image_thumbnail: str | None
    featured: bool
    author_id: uuid.UUID
    editor_id: uuid.UUID | None
    publication_date: date | None
    submitted_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None
    sections: list[NewsSectionResponse]
    tags: list[TagResponse]
    revisions: list[NewsRevisionResponse]


class NewsPage(BaseModel):
    items: list[NewsResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
