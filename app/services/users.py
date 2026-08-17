import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.users import User
from app.roles import Role
from app.schemas import RoleUpdate


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())))


def update_role(user_id: uuid.UUID, data: RoleUpdate, db: Session, administrator: User) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id == administrator.id and data.role != Role.ADMIN:
        raise HTTPException(status_code=400, detail="No puedes retirar tu propio rol de administrador")
    user.role = data.role.value
    db.commit()
    db.refresh(user)
    return user
