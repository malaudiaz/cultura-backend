import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.roles import Role
from app.security import JWT_ALGORITHM, JWT_SECRET


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o vencido",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials or credentials.scheme.lower() != "bearer":
        raise unauthorized

    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat"]},
        )
        if payload.get("type") != "access":
            raise unauthorized
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, TypeError, KeyError) as exc:
        raise unauthorized from exc

    user = db.get(User, user_id)
    if not user:
        raise unauthorized
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*allowed_roles: Role):
    def dependency(user: CurrentUser) -> User:
        try:
            role = Role(user.role)
        except ValueError as exc:
            raise HTTPException(status_code=403, detail="Rol de usuario inválido") from exc
        if role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="No tienes el rol requerido para realizar esta acción",
            )
        return user

    return dependency
