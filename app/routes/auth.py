from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.exceptions import GoogleAuthError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.users import User
from app.providers import SocialProfile, verify_facebook_token, verify_google_token
from app.schemas import AuthResponse, LocalLogin, LocalRegister, SocialToken
from app.security import create_access_token, hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["autenticación"])
DbSession = Annotated[Session, Depends(get_db)]


def auth_response(user: User) -> AuthResponse:
    return AuthResponse(access_token=create_access_token(user.id), user=user)


@router.post(
    "/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
def register(data: LocalRegister, db: DbSession) -> AuthResponse:
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="El correo ya está registrado")

    user = User(
        email=email, name=data.name.strip(), password_hash=hash_password(data.password)
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="El correo ya está registrado"
        ) from exc
    db.refresh(user)
    return auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(data: LocalLogin, db: DbSession) -> AuthResponse:
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if (
        not user
        or not user.password_hash
        or not verify_password(data.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    return auth_response(user)


def social_auth(
    provider: Literal["google", "facebook"], profile: SocialProfile, db: Session
) -> AuthResponse:
    provider_column = User.google_id if provider == "google" else User.facebook_id
    user = db.scalar(select(User).where(provider_column == profile.provider_id))
    if user:
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Usuario inactivo")
        return auth_response(user)

    if db.scalar(select(User).where(User.email == profile.email)):
        raise HTTPException(
            status_code=409,
            detail="El correo ya pertenece a otra cuenta; inicia sesión y vincula el proveedor",
        )

    values = {
        "google_id" if provider == "google" else "facebook_id": profile.provider_id
    }
    user = User(email=profile.email, name=profile.name, **values)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="La cuenta ya está registrada"
        ) from exc
    db.refresh(user)
    return auth_response(user)


@router.post("/google", response_model=AuthResponse)
def google_auth(data: SocialToken, db: DbSession) -> AuthResponse:
    try:
        profile = verify_google_token(data.token)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GoogleAuthError as exc:
        raise HTTPException(
            status_code=503, detail="No se pudo contactar con Google"
        ) from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Token de Google inválido") from exc
    return social_auth("google", profile, db)


@router.post("/facebook", response_model=AuthResponse)
def facebook_auth(data: SocialToken, db: DbSession) -> AuthResponse:
    try:
        profile = verify_facebook_token(data.token)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(
            status_code=401, detail="Token de Facebook inválido"
        ) from exc
    return social_auth("facebook", profile, db)
