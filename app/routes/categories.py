import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.categories import Category
from app.models.gallery import GalleryImage
from app.models.users import User
from app.roles import Role
from app.schemas import CategoryCreate, CategoryResponse


router = APIRouter(prefix="/categories", tags=["category"])
DbSession = Annotated[Session, Depends(get_db)]
Manager = Annotated[User, Depends(require_role(Role.ADMIN, Role.EDITOR))]


@router.get("", response_model=list[CategoryResponse])
def list_categories(db: DbSession) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name)))


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreate, db: DbSession, _: Manager) -> Category:
    category = Category(name=data.name)
    db.add(category)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Ya existe una categoría con ese nombre"
        ) from exc
    db.refresh(category)
    return category


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: uuid.UUID, data: CategoryCreate, db: DbSession, _: Manager
) -> Category:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    category.name = data.name
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Ya existe una categoría con ese nombre"
        ) from exc
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: uuid.UUID, db: DbSession, _: Manager) -> None:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    if db.scalar(
        select(func.count())
        .select_from(GalleryImage)
        .where(GalleryImage.category_id == category_id)
    ):
        raise HTTPException(
            status_code=409, detail="No se puede eliminar una categoría con imágenes"
        )
    db.delete(category)
    db.commit()
