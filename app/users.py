import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_role
from app.models import User
from app.roles import Role
from app.schemas import RoleUpdate, UserResponse


router = APIRouter(prefix="/users", tags=["usuarios"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser) -> User:
    return user


@router.get("", response_model=list[UserResponse])
def list_users(
    db: DbSession,
    _: Annotated[User, Depends(require_role(Role.ADMIN))],
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())))


@router.patch("/{user_id}/role", response_model=UserResponse)
def update_role(
    user_id: uuid.UUID,
    data: RoleUpdate,
    db: DbSession,
    administrator: Annotated[User, Depends(require_role(Role.ADMIN))],
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id == administrator.id and data.role != Role.ADMIN:
        raise HTTPException(status_code=400, detail="No puedes retirar tu propio rol de administrador")

    user.role = data.role.value
    db.commit()
    db.refresh(user)
    return user
