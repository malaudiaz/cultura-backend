import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app.routes.auth import router as auth_router
from app.routes.gallery import (
    MEDIA_DIRECTORY,
    ensure_media_directory,
    router as gallery_router,
)
from app.routes.users import router as users_router
from app.database import Base, engine
from app import models  # noqa: F401


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_media_directory()
    Base.metadata.create_all(bind=engine)
    # `create_all` no modifica tablas que ya existen. Esta actualización ligera
    # mantiene compatibles las instalaciones creadas antes de registrar autoría.
    if engine.dialect.name == "postgresql":
        columns = {
            column["name"] for column in inspect(engine).get_columns("gallery_images")
        }
        with engine.begin() as connection:
            if "uploaded_by_id" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE gallery_images "
                        "ADD COLUMN uploaded_by_id UUID REFERENCES users(id) ON DELETE SET NULL"
                    )
                )
            if "media_type" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE gallery_images ADD COLUMN media_type VARCHAR(10) "
                        "NOT NULL DEFAULT 'image'"
                    )
                )
            if "duration_seconds" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE gallery_images ADD COLUMN duration_seconds DOUBLE PRECISION"
                    )
                )
    yield


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
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(gallery_router)
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
