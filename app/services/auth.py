from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.users import User
from app.providers import SocialProfile
from app.schemas import AuthResponse, LocalLogin, LocalRegister
from app.security import create_access_token, hash_password, verify_password


def auth_response(user: User) -> AuthResponse:
    return AuthResponse(access_token=create_access_token(user.id), user=user)


def register(data: LocalRegister, db: Session) -> AuthResponse:
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="El correo ya está registrado")
    user = User(email=email, name=data.name.strip(), password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El correo ya está registrado") from exc
    db.refresh(user)
    return auth_response(user)


def login(data: LocalLogin, db: Session) -> AuthResponse:
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Correo o contraseña incorrectos")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    return auth_response(user)


def social_auth(provider: Literal["google", "facebook"], profile: SocialProfile, db: Session) -> AuthResponse:
    provider_column = User.google_id if provider == "google" else User.facebook_id
    user = db.scalar(select(User).where(provider_column == profile.provider_id))
    if user:
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Usuario inactivo")
        return auth_response(user)
    if db.scalar(select(User).where(User.email == profile.email)):
        raise HTTPException(status_code=409, detail="El correo ya pertenece a otra cuenta; inicia sesión y vincula el proveedor")
    values = {"google_id" if provider == "google" else "facebook_id": profile.provider_id}
    user = User(email=profile.email, name=profile.name, **values)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="La cuenta ya está registrada") from exc
    db.refresh(user)
    return auth_response(user)
