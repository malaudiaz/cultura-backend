import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.categories import Category
from app.models.users import User
from app.roles import Role
from app.schemas import CategoryCreate, CategoryResponse
from app.services import categories as categories_service


router = APIRouter(prefix="/categories", tags=["category"])
DbSession = Annotated[Session, Depends(get_db)]
Manager = Annotated[User, Depends(require_role(Role.ADMIN, Role.EDITOR))]


@router.get("", response_model=list[CategoryResponse])
def list_categories(db: DbSession) -> list[Category]:
    return categories_service.list_categories(db)


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreate, db: DbSession, _: Manager) -> Category:
    return categories_service.create_category(data, db)


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: uuid.UUID, data: CategoryCreate, db: DbSession, _: Manager) -> Category:
    return categories_service.update_category(category_id, data, db)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: uuid.UUID, db: DbSession, _: Manager) -> None:
    categories_service.delete_category(category_id, db)
