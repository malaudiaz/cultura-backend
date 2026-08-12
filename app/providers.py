import hashlib
import hmac
import os
from dataclasses import dataclass

import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token


@dataclass(frozen=True)
class SocialProfile:
    provider_id: str
    email: str
    name: str


def verify_google_token(token: str) -> SocialProfile:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise RuntimeError("GOOGLE_CLIENT_ID no está configurado")

    claims = id_token.verify_oauth2_token(
        token, google_requests.Request(), audience=client_id
    )
    if not claims.get("email") or not claims.get("email_verified"):
        raise ValueError("Google no proporcionó un correo verificado")

    return SocialProfile(
        provider_id=claims["sub"],
        email=claims["email"].lower(),
        name=claims.get("name") or claims["email"].split("@", 1)[0],
    )


def verify_facebook_token(token: str) -> SocialProfile:
    app_id = os.getenv("FACEBOOK_APP_ID")
    app_secret = os.getenv("FACEBOOK_APP_SECRET")
    if not app_id or not app_secret:
        raise RuntimeError("Las credenciales de Facebook no están configuradas")

    app_token = f"{app_id}|{app_secret}"
    appsecret_proof = hmac.new(
        app_secret.encode(), token.encode(), hashlib.sha256
    ).hexdigest()

    with httpx.Client(timeout=10) as client:
        debug_response = client.get(
            "https://graph.facebook.com/debug_token",
            params={"input_token": token, "access_token": app_token},
        )
        debug_response.raise_for_status()
        debug_data = debug_response.json().get("data", {})
        if (
            not debug_data.get("is_valid")
            or debug_data.get("app_id") != app_id
            or not debug_data.get("user_id")
        ):
            raise ValueError("Token de Facebook inválido")

        profile_response = client.get(
            "https://graph.facebook.com/me",
            params={
                "fields": "id,name,email",
                "access_token": token,
                "appsecret_proof": appsecret_proof,
            },
        )
        profile_response.raise_for_status()
        profile = profile_response.json()

    if profile.get("id") != debug_data["user_id"] or not profile.get("email"):
        raise ValueError("Facebook no proporcionó el correo del usuario")

    return SocialProfile(
        provider_id=profile["id"],
        email=profile["email"].lower(),
        name=profile.get("name") or profile["email"].split("@", 1)[0],
    )
