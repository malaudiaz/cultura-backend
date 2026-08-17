import uuid
from datetime import datetime
from math import ceil

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.categories import Category
from app.models.news import News, NewsRevision, NewsSection, NewsTag, Tag
from app.models.users import User
from app.roles import Role
from app.schemas import NewsCreate, NewsPage, NewsPublish, NewsResponse, NewsReview, NewsRevisionResponse, NewsSectionCreate, NewsSectionResponse, NewsSectionUpdate, NewsUpdate, TagCreate, TagResponse, TagUpdate


PAGE_SIZE = 10


def news_options():
    return selectinload(News.sections), selectinload(News.tag_links).selectinload(NewsTag.tag), selectinload(News.revisions)


def response(news: News) -> NewsResponse:
    return NewsResponse(
        id=news.id, title=news.title, slug=news.slug, category_id=news.category_id, status=news.status,
        summary=news.summary, image=news.image, image_thumbnail=news.image_thumbnail, featured=news.featured,
        author_id=news.author_id, editor_id=news.editor_id, publication_date=news.publication_date,
        submitted_at=news.submitted_at, notes=news.notes, created_at=news.created_at, updated_at=news.updated_at,
        deleted_at=news.deleted_at,
        sections=[NewsSectionResponse.model_validate(section) for section in news.sections if section.deleted_at is None],
        tags=[TagResponse.model_validate(link.tag) for link in news.tag_links],
        revisions=[NewsRevisionResponse.model_validate(revision) for revision in news.revisions],
    )


def get_news(db: Session, news_id: uuid.UUID) -> News:
    news = db.scalar(select(News).options(*news_options()).where(News.id == news_id))
    if not news or news.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Noticia no encontrada")
    return news


def ensure_owner_or_editor(news: News, user: User) -> None:
    if user.role not in {Role.ADMIN, Role.EDITOR} and news.author_id != user.id:
        raise HTTPException(status_code=403, detail="No puedes modificar esta noticia")


def set_tags(db: Session, news: News, tag_ids: list[uuid.UUID]) -> None:
    tags = list(db.scalars(select(Tag).where(Tag.id.in_(set(tag_ids))))) if tag_ids else []
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status_code=422, detail="Una o más etiquetas no existen")
    news.tag_links = [NewsTag(tag=tag) for tag in tags]


def list_published_news(db: Session, page: int, category_id: uuid.UUID | None, featured: bool | None) -> NewsPage:
    filters = [News.status == "published", News.deleted_at.is_(None)]
    if category_id:
        filters.append(News.category_id == category_id)
    if featured is not None:
        filters.append(News.featured == featured)
    total = db.scalar(select(func.count()).select_from(News).where(*filters)) or 0
    items = list(db.scalars(select(News).options(*news_options()).where(*filters).order_by(News.publication_date.desc(), News.created_at.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)))
    return NewsPage(items=[response(item) for item in items], total=total, page=page, page_size=PAGE_SIZE, total_pages=ceil(total / PAGE_SIZE) if total else 0)


def list_my_news(db: Session, user: User) -> list[NewsResponse]:
    items = list(db.scalars(select(News).options(*news_options()).where(News.author_id == user.id, News.deleted_at.is_(None)).order_by(News.created_at.desc())))
    return [response(item) for item in items]


def list_tags(db: Session) -> list[Tag]:
    return list(db.scalars(select(Tag).order_by(Tag.name)))


def create_tag(data: TagCreate, db: Session) -> Tag:
    tag = Tag(**data.model_dump())
    db.add(tag)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="La etiqueta ya existe") from exc
    db.refresh(tag)
    return tag


def update_tag(tag_id: uuid.UUID, data: TagUpdate, db: Session) -> Tag:
    tag = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Etiqueta no encontrada")
    tag.name = data.name
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="La etiqueta ya existe") from exc
    db.refresh(tag)
    return tag


def delete_tag(tag_id: uuid.UUID, db: Session) -> None:
    tag = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Etiqueta no encontrada")
    if db.scalar(select(func.count()).select_from(NewsTag).where(NewsTag.tag_id == tag.id)):
        raise HTTPException(status_code=409, detail="No se puede eliminar una etiqueta en uso")
    db.delete(tag)
    db.commit()


def get_published_news(slug: str, db: Session) -> NewsResponse:
    news = db.scalar(select(News).options(*news_options()).where(News.slug == slug, News.status == "published", News.deleted_at.is_(None)))
    if not news:
        raise HTTPException(status_code=404, detail="Noticia no encontrada")
    return response(news)


def get_news_for_user(news_id: uuid.UUID, db: Session, user: User) -> NewsResponse:
    news = get_news(db, news_id)
    ensure_owner_or_editor(news, user)
    return response(news)


def create_news(data: NewsCreate, db: Session, user: User) -> NewsResponse:
    if not db.get(Category, data.category_id):
        raise HTTPException(status_code=422, detail="Categoría no encontrada")
    news = News(**data.model_dump(exclude={"sections", "tag_ids"}), author_id=user.id)
    news.sections = [NewsSection(**section.model_dump()) for section in data.sections]
    set_tags(db, news, data.tag_ids)
    db.add(news)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El slug ya existe") from exc
    return response(get_news(db, news.id))


def update_news(news_id: uuid.UUID, data: NewsUpdate, db: Session, user: User) -> NewsResponse:
    news = get_news(db, news_id)
    ensure_owner_or_editor(news, user)
    changes = data.model_dump(exclude_unset=True, exclude={"tag_ids"})
    if "category_id" in changes and not db.get(Category, changes["category_id"]):
        raise HTTPException(status_code=422, detail="Categoría no encontrada")
    for field, value in changes.items():
        setattr(news, field, value)
    if data.tag_ids is not None:
        set_tags(db, news, data.tag_ids)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El slug ya existe") from exc
    return response(get_news(db, news.id))


def submit_news(news_id: uuid.UUID, db: Session, user: User) -> NewsResponse:
    news = get_news(db, news_id)
    ensure_owner_or_editor(news, user)
    news.status = "in_review"
    news.submitted_at = datetime.now().astimezone()
    db.commit()
    return response(get_news(db, news.id))


def review_news(news_id: uuid.UUID, data: NewsReview, db: Session, user: User) -> NewsResponse:
    news = get_news(db, news_id)
    news.status, news.editor_id, news.notes = data.status, user.id, data.notes
    news.revisions.append(NewsRevision(editor_id=user.id, action=data.status, notes=data.notes))
    db.commit()
    return response(get_news(db, news.id))


def publish_news(news_id: uuid.UUID, data: NewsPublish, db: Session, user: User) -> NewsResponse:
    news = get_news(db, news_id)
    news.status, news.editor_id = "published", user.id
    news.publication_date = data.publication_date or datetime.now().date()
    if data.notes is not None:
        news.notes = data.notes
    news.revisions.append(NewsRevision(editor_id=user.id, action="published", notes=data.notes))
    db.commit()
    return response(get_news(db, news.id))


def delete_news(news_id: uuid.UUID, db: Session, user: User) -> None:
    news = get_news(db, news_id)
    ensure_owner_or_editor(news, user)
    news.deleted_at = datetime.now().astimezone()
    db.commit()


def create_section(news_id: uuid.UUID, data: NewsSectionCreate, db: Session, user: User) -> NewsSection:
    news = get_news(db, news_id)
    ensure_owner_or_editor(news, user)
    section = NewsSection(news_id=news.id, **data.model_dump())
    db.add(section)
    db.commit()
    db.refresh(section)
    return section


def update_section(news_id: uuid.UUID, section_id: uuid.UUID, data: NewsSectionUpdate, db: Session, user: User) -> NewsSection:
    news = get_news(db, news_id)
    ensure_owner_or_editor(news, user)
    section = db.scalar(select(NewsSection).where(NewsSection.id == section_id, NewsSection.news_id == news.id, NewsSection.deleted_at.is_(None)))
    if not section:
        raise HTTPException(status_code=404, detail="Sección no encontrada")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(section, field, value)
    db.commit()
    db.refresh(section)
    return section


def delete_section(news_id: uuid.UUID, section_id: uuid.UUID, db: Session, user: User) -> None:
    news = get_news(db, news_id)
    ensure_owner_or_editor(news, user)
    section = db.scalar(select(NewsSection).where(NewsSection.id == section_id, NewsSection.news_id == news.id, NewsSection.deleted_at.is_(None)))
    if not section:
        raise HTTPException(status_code=404, detail="Sección no encontrada")
    section.deleted_at = datetime.now().astimezone()
    db.commit()
