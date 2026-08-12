import io
import json
import logging
import os
import shutil
import subprocess
import uuid
from math import ceil
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import require_role
from app.models import Category, GalleryImage, User
from app.roles import Role
from app.schemas import (
    CategoryCreate,
    CategoryResponse,
    GalleryImagePage,
    GalleryImageResponse,
)


router = APIRouter(prefix="/gallery", tags=["galería"])
logger = logging.getLogger(__name__)
DbSession = Annotated[Session, Depends(get_db)]
Manager = Annotated[User, Depends(require_role(Role.ADMIN, Role.EDITOR))]
Uploader = Annotated[
    User,
    Depends(require_role(Role.ADMIN, Role.EDITOR, Role.WRITER)),
]
PAGE_SIZE = 10
MEDIA_DIRECTORY = Path(os.getenv("IMAGE_STORAGE_PATH", "/app/media"))
SUPPORTED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
VIDEO_CONTENT_TYPE = "video/mp4"
MIN_VIDEO_SIZE_BYTES = 3 * 1024 * 1024
MAX_VIDEO_SIZE_BYTES = 8 * 1024 * 1024
MIN_VIDEO_DURATION_SECONDS = 15
MAX_VIDEO_DURATION_SECONDS = 30


def ensure_media_directory() -> None:
    MEDIA_DIRECTORY.mkdir(parents=True, exist_ok=True)


def _image_response(image: GalleryImage, request: Request) -> GalleryImageResponse:
    return GalleryImageResponse(
        id=image.id,
        category_id=image.category_id,
        category_name=image.category.name,
        uploaded_by_id=image.uploaded_by_id,
        uploaded_by_name=image.uploaded_by.name if image.uploaded_by else None,
        media_type=image.media_type,
        duration_seconds=image.duration_seconds,
        url=str(request.url_for("media", path=image.filename)),
        created_at=image.created_at,
    )


def _save_as_webp(upload: UploadFile) -> str:
    if upload.content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Solo se admiten imágenes JPEG, PNG o WebP")

    try:
        content = upload.file.read()
        with Image.open(io.BytesIO(content)) as source:
            source.verify()
        with Image.open(io.BytesIO(content)) as source:
            # Convertir a RGB/RGBA evita errores de Pillow con paletas y CMYK.
            converted = source.convert("RGBA" if "A" in source.getbands() else "RGB")
            filename = f"{uuid.uuid4()}.webp"
            path = MEDIA_DIRECTORY / filename
            converted.save(path, format="WEBP", quality=80, method=6)
            return filename
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="El archivo no es una imagen válida") from exc
    finally:
        upload.file.seek(0)


def _video_duration_seconds(path: Path) -> float:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type:format=duration",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        metadata = json.loads(result.stdout)
        if not any(stream.get("codec_type") == "video" for stream in metadata["streams"]):
            raise ValueError("No contiene una pista de video")
        return float(metadata["format"]["duration"])
    except (FileNotFoundError, subprocess.SubprocessError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="El archivo no es un video MP4 válido") from exc


def _save_promotional_video(upload: UploadFile) -> tuple[str, float]:
    if upload.content_type != VIDEO_CONTENT_TYPE:
        raise HTTPException(status_code=415, detail="Solo se admiten videos MP4")

    upload.file.seek(0, os.SEEK_END)
    size = upload.file.tell()
    upload.file.seek(0)
    if not MIN_VIDEO_SIZE_BYTES <= size <= MAX_VIDEO_SIZE_BYTES:
        raise HTTPException(status_code=422, detail="El video debe pesar entre 3 y 8 MB")

    filename = f"{uuid.uuid4()}.mp4"
    path = MEDIA_DIRECTORY / filename
    try:
        with path.open("wb") as destination:
            shutil.copyfileobj(upload.file, destination)
        duration = _video_duration_seconds(path)
        if not MIN_VIDEO_DURATION_SECONDS <= duration <= MAX_VIDEO_DURATION_SECONDS:
            raise HTTPException(status_code=422, detail="El video debe durar entre 15 y 30 segundos")
        return filename, duration
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        upload.file.seek(0)


def _save_media(upload: UploadFile) -> tuple[str, str, float | None]:
    if upload.content_type == VIDEO_CONTENT_TYPE:
        filename, duration = _save_promotional_video(upload)
        return filename, "video", duration
    return _save_as_webp(upload), "image", None


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(db: DbSession) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name)))


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreate, db: DbSession, _: Manager) -> Category:
    category = Category(name=data.name)
    db.add(category)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una categoría con ese nombre") from exc
    db.refresh(category)
    return category


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
def update_category(category_id: uuid.UUID, data: CategoryCreate, db: DbSession, _: Manager) -> Category:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    category.name = data.name
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una categoría con ese nombre") from exc
    db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: uuid.UUID, db: DbSession, _: Manager) -> None:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    if db.scalar(select(func.count()).select_from(GalleryImage).where(GalleryImage.category_id == category_id)):
        raise HTTPException(status_code=409, detail="No se puede eliminar una categoría con imágenes")
    db.delete(category)
    db.commit()


@router.post("/images", response_model=list[GalleryImageResponse], status_code=status.HTTP_201_CREATED)
def upload_images(
    request: Request,
    category_id: Annotated[uuid.UUID, Form()],
    files: Annotated[list[UploadFile], File()],
    db: DbSession,
    manager: Uploader,
) -> list[GalleryImageResponse]:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    if not files:
        raise HTTPException(status_code=422, detail="Debes enviar al menos una imagen")

    ensure_media_directory()
    filenames: list[str] = []
    try:
        uploaded_media = [_save_media(upload) for upload in files]
        filenames = [filename for filename, _, _ in uploaded_media]
        images = [
            GalleryImage(
                category_id=category.id,
                filename=filename,
                uploaded_by_id=manager.id,
                media_type=media_type,
                duration_seconds=duration_seconds,
            )
            for filename, media_type, duration_seconds in uploaded_media
        ]
        db.add_all(images)
        db.commit()
        for image in images:
            db.refresh(image)
        return [_image_response(image, request) for image in images]
    except Exception:
        db.rollback()
        for filename in filenames:
            try:
                (MEDIA_DIRECTORY / filename).unlink(missing_ok=True)
            except OSError:
                logger.exception("No se pudo eliminar el archivo temporal %s", filename)
        raise


@router.get("/images", response_model=GalleryImagePage)
def list_images(
    request: Request,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    category_id: uuid.UUID | None = None,
) -> GalleryImagePage:
    filters = [] if category_id is None else [GalleryImage.category_id == category_id]
    total = db.scalar(select(func.count()).select_from(GalleryImage).where(*filters)) or 0
    images = list(
        db.scalars(
            select(GalleryImage)
            .options(
                joinedload(GalleryImage.category),
                joinedload(GalleryImage.uploaded_by),
            )
            .where(*filters)
            .order_by(GalleryImage.created_at.desc(), GalleryImage.id.desc())
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE)
        )
    )
    return GalleryImagePage(
        items=[_image_response(image, request) for image in images],
        total=total,
        page=page,
        page_size=PAGE_SIZE,
        total_pages=ceil(total / PAGE_SIZE) if total else 0,
    )


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(image_id: uuid.UUID, db: DbSession, _: Manager) -> None:
    image = db.get(GalleryImage, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    filename = image.filename
    db.delete(image)
    db.commit()
    try:
        (MEDIA_DIRECTORY / filename).unlink(missing_ok=True)
    except OSError:
        logger.exception("No se pudo eliminar el archivo de imagen %s", filename)
