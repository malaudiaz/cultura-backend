import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.news import NewsSection, Tag
from app.models.users import User
from app.roles import Role
from app.schemas import NewsCreate, NewsPage, NewsPublish, NewsResponse, NewsReview, NewsSectionCreate, NewsSectionResponse, NewsSectionUpdate, NewsUpdate, TagCreate, TagResponse, TagUpdate
from app.services import news as news_service


router = APIRouter(prefix="/news", tags=["news"])
DbSession = Annotated[Session, Depends(get_db)]
Writer = Annotated[User, Depends(require_role(Role.ADMIN, Role.EDITOR, Role.WRITER))]
Editor = Annotated[User, Depends(require_role(Role.ADMIN, Role.EDITOR))]


@router.get("", response_model=NewsPage)
def list_published_news(db: DbSession, page: Annotated[int, Query(ge=1)] = 1, category_id: uuid.UUID | None = None, featured: bool | None = None) -> NewsPage:
    return news_service.list_published_news(db, page, category_id, featured)


@router.get("/mine", response_model=list[NewsResponse])
def list_my_news(db: DbSession, user: Writer) -> list[NewsResponse]:
    return news_service.list_my_news(db, user)


@router.get("/tags", response_model=list[TagResponse])
def list_tags(db: DbSession) -> list[Tag]:
    return news_service.list_tags(db)


@router.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(data: TagCreate, db: DbSession, _: Editor) -> Tag:
    return news_service.create_tag(data, db)


@router.patch("/tags/{tag_id}", response_model=TagResponse)
def update_tag(tag_id: uuid.UUID, data: TagUpdate, db: DbSession, _: Editor) -> Tag:
    return news_service.update_tag(tag_id, data, db)


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: uuid.UUID, db: DbSession, _: Editor) -> None:
    news_service.delete_tag(tag_id, db)


@router.get("/slug/{slug}", response_model=NewsResponse)
def get_published_news(slug: str, db: DbSession) -> NewsResponse:
    return news_service.get_published_news(slug, db)


@router.get("/{news_id}", response_model=NewsResponse)
def get_news(news_id: uuid.UUID, db: DbSession, user: Writer) -> NewsResponse:
    return news_service.get_news_for_user(news_id, db, user)


@router.post("", response_model=NewsResponse, status_code=status.HTTP_201_CREATED)
def create_news(data: NewsCreate, db: DbSession, user: Writer) -> NewsResponse:
    return news_service.create_news(data, db, user)


@router.patch("/{news_id}", response_model=NewsResponse)
def update_news(news_id: uuid.UUID, data: NewsUpdate, db: DbSession, user: Writer) -> NewsResponse:
    return news_service.update_news(news_id, data, db, user)


@router.post("/{news_id}/submit", response_model=NewsResponse)
def submit_news(news_id: uuid.UUID, db: DbSession, user: Writer) -> NewsResponse:
    return news_service.submit_news(news_id, db, user)


@router.post("/{news_id}/review", response_model=NewsResponse)
def review_news(news_id: uuid.UUID, data: NewsReview, db: DbSession, user: Editor) -> NewsResponse:
    return news_service.review_news(news_id, data, db, user)


@router.post("/{news_id}/publish", response_model=NewsResponse)
def publish_news(news_id: uuid.UUID, data: NewsPublish, db: DbSession, user: Editor) -> NewsResponse:
    return news_service.publish_news(news_id, data, db, user)


@router.delete("/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_news(news_id: uuid.UUID, db: DbSession, user: Writer) -> None:
    news_service.delete_news(news_id, db, user)


@router.post("/{news_id}/sections", response_model=NewsSectionResponse, status_code=status.HTTP_201_CREATED)
def create_section(news_id: uuid.UUID, data: NewsSectionCreate, db: DbSession, user: Writer) -> NewsSection:
    return news_service.create_section(news_id, data, db, user)


@router.patch("/{news_id}/sections/{section_id}", response_model=NewsSectionResponse)
def update_section(news_id: uuid.UUID, section_id: uuid.UUID, data: NewsSectionUpdate, db: DbSession, user: Writer) -> NewsSection:
    return news_service.update_section(news_id, section_id, data, db, user)


@router.delete("/{news_id}/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_section(news_id: uuid.UUID, section_id: uuid.UUID, db: DbSession, user: Writer) -> None:
    news_service.delete_section(news_id, section_id, db, user)
