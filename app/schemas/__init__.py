"""Esquemas Pydantic organizados por dominio.

Este módulo conserva una API de importación única para las rutas, mientras los
esquemas crecen en archivos independientes.
"""

from app.schemas.auth import AuthResponse, LocalLogin, LocalRegister, SocialToken
from app.schemas.gallery import (
    CategoryCreate,
    CategoryResponse,
    GalleryImagePage,
    GalleryImageResponse,
)
from app.schemas.news import (
    NewsCreate,
    NewsPage,
    NewsPublish,
    NewsResponse,
    NewsReview,
    NewsRevisionResponse,
    NewsSectionCreate,
    NewsSectionResponse,
    NewsSectionUpdate,
    NewsUpdate,
    TagCreate,
    TagResponse,
    TagUpdate,
)
from app.schemas.users import RoleUpdate, UserResponse

__all__ = [
    "AuthResponse",
    "CategoryCreate",
    "CategoryResponse",
    "GalleryImagePage",
    "GalleryImageResponse",
    "LocalLogin",
    "LocalRegister",
    "NewsCreate",
    "NewsPage",
    "NewsPublish",
    "NewsResponse",
    "NewsReview",
    "NewsRevisionResponse",
    "NewsSectionCreate",
    "NewsSectionResponse",
    "NewsSectionUpdate",
    "NewsUpdate",
    "RoleUpdate",
    "SocialToken",
    "TagCreate",
    "TagResponse",
    "TagUpdate",
    "UserResponse",
]
