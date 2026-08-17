import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.routes.auth import router as auth_router
from app.routes.categories import router as categories_router
from app.routes.gallery import (
    MEDIA_DIRECTORY,
    ensure_media_directory,
    router as gallery_router,
)
from app.routes.news import router as news_router
from app.routes.users import router as users_router
from app.database import engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_media_directory()
    yield


API_V1_PREFIX = "/api/v1"

app = FastAPI(title="FastAPI + PostgreSQL", lifespan=lifespan)
cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix=API_V1_PREFIX)
app.include_router(categories_router, prefix=API_V1_PREFIX)
app.include_router(users_router, prefix=API_V1_PREFIX)
app.include_router(gallery_router, prefix=API_V1_PREFIX)
app.include_router(news_router, prefix=API_V1_PREFIX)
app.mount(
    "/media", StaticFiles(directory=MEDIA_DIRECTORY, check_dir=False), name="media"
)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "API funcionando"}


@app.get("/health")
def health() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="Base de datos no disponible"
        ) from exc

    return {"status": "ok", "database": "connected"}
