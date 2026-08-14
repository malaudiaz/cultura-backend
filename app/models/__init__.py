"""Modelos ORM expuestos desde un único punto de importación.

Importarlos aquí asegura que SQLAlchemy registre todas las tablas antes de
ejecutar ``Base.metadata.create_all()``.
"""

from app.models.categories import Category
from app.models.gallery import GalleryImage
from app.models.news import News, NewsRevision, NewsSection, NewsTag, Tag
from app.models.users import User

__all__ = [
    "Category",
    "GalleryImage",
    "News",
    "NewsRevision",
    "NewsSection",
    "NewsTag",
    "Tag",
    "User",
]
