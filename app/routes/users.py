import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_role
from app.models.users import User
from app.roles import Role
from app.schemas import RoleUpdate, UserResponse
from app.services import users as users_service


router = APIRouter(prefix="/users", tags=["usuarios"])
DbSession = Annotated[Session, Depends(get_db)]
Administrator = Annotated[User, Depends(require_role(Role.ADMIN))]


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser) -> User:
    return user


@router.get("", response_model=list[UserResponse])
def list_users(db: DbSession, _: Administrator) -> list[User]:
    return users_service.list_users(db)


@router.patch("/{user_id}/role", response_model=UserResponse)
def update_role(user_id: uuid.UUID, data: RoleUpdate, db: DbSession, administrator: Administrator) -> User:
    return users_service.update_role(user_id, data, db, administrator)
