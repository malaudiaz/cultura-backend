import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.categories import Category
from app.models.gallery import GalleryImage
from app.schemas import CategoryCreate


def list_categories(db: Session) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name)))


def create_category(data: CategoryCreate, db: Session) -> Category:
    category = Category(name=data.name)
    db.add(category)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una categoría con ese nombre") from exc
    db.refresh(category)
    return category


def update_category(category_id: uuid.UUID, data: CategoryCreate, db: Session) -> Category:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    category.name = data.name
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una categoría con ese nombre") from exc
    db.refresh(category)
    return category


def delete_category(category_id: uuid.UUID, db: Session) -> None:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    if db.scalar(select(func.count()).select_from(GalleryImage).where(GalleryImage.category_id == category_id)):
        raise HTTPException(status_code=409, detail="No se puede eliminar una categoría con imágenes")
    db.delete(category)
    db.commit()
