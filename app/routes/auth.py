from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.exceptions import GoogleAuthError
from sqlalchemy.orm import Session

from app.database import get_db
from app.providers import verify_facebook_token, verify_google_token
from app.schemas import AuthResponse, LocalLogin, LocalRegister, SocialToken
from app.services import auth as auth_service


router = APIRouter(prefix="/auth", tags=["autenticación"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(data: LocalRegister, db: DbSession) -> AuthResponse:
    return auth_service.register(data, db)


@router.post("/login", response_model=AuthResponse)
def login(data: LocalLogin, db: DbSession) -> AuthResponse:
    return auth_service.login(data, db)


@router.post("/google", response_model=AuthResponse)
def google_auth(data: SocialToken, db: DbSession) -> AuthResponse:
    try:
        profile = verify_google_token(data.token)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GoogleAuthError as exc:
        raise HTTPException(status_code=503, detail="No se pudo contactar con Google") from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Token de Google inválido") from exc
    return auth_service.social_auth("google", profile, db)


@router.post("/facebook", response_model=AuthResponse)
def facebook_auth(data: SocialToken, db: DbSession) -> AuthResponse:
    try:
        profile = verify_facebook_token(data.token)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=401, detail="Token de Facebook inválido") from exc
    return auth_service.social_auth("facebook", profile, db)
