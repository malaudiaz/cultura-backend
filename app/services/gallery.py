import io
import json
import logging
import os
import shutil
import subprocess
import uuid
from math import ceil
from pathlib import Path

from fastapi import HTTPException, Request, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.categories import Category
from app.models.gallery import GalleryImage
from app.models.users import User
from app.schemas import GalleryImagePage, GalleryImageResponse


logger = logging.getLogger(__name__)
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


def image_response(image: GalleryImage, request: Request) -> GalleryImageResponse:
    return GalleryImageResponse(
        id=image.id, category_id=image.category_id, category_name=image.category.name,
        uploaded_by_id=image.uploaded_by_id,
        uploaded_by_name=image.uploaded_by.name if image.uploaded_by else None,
        media_type=image.media_type, duration_seconds=image.duration_seconds,
        url=str(request.url_for("media", path=image.filename)), created_at=image.created_at,
    )


def save_as_webp(upload: UploadFile) -> str:
    if upload.content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Solo se admiten imágenes JPEG, PNG o WebP")
    try:
        content = upload.file.read()
        with Image.open(io.BytesIO(content)) as source:
            source.verify()
        with Image.open(io.BytesIO(content)) as source:
            converted = source.convert("RGBA" if "A" in source.getbands() else "RGB")
            filename = f"{uuid.uuid4()}.webp"
            converted.save(MEDIA_DIRECTORY / filename, format="WEBP", quality=80, method=6)
            return filename
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="El archivo no es una imagen válida") from exc
    finally:
        upload.file.seek(0)


def video_duration_seconds(path: Path) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration", "-of", "json", str(path)],
            check=True, capture_output=True, text=True, timeout=15,
        )
        metadata = json.loads(result.stdout)
        if not any(stream.get("codec_type") == "video" for stream in metadata["streams"]):
            raise ValueError("No contiene una pista de video")
        return float(metadata["format"]["duration"])
    except (FileNotFoundError, subprocess.SubprocessError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="El archivo no es un video MP4 válido") from exc


def save_promotional_video(upload: UploadFile) -> tuple[str, float]:
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
        duration = video_duration_seconds(path)
        if not MIN_VIDEO_DURATION_SECONDS <= duration <= MAX_VIDEO_DURATION_SECONDS:
            raise HTTPException(status_code=422, detail="El video debe durar entre 15 y 30 segundos")
        return filename, duration
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        upload.file.seek(0)


def save_media(upload: UploadFile) -> tuple[str, str, float | None]:
    if upload.content_type == VIDEO_CONTENT_TYPE:
        filename, duration = save_promotional_video(upload)
        return filename, "video", duration
    return save_as_webp(upload), "image", None


def upload_images(request: Request, category_id: uuid.UUID, files: list[UploadFile], db: Session, user: User) -> list[GalleryImageResponse]:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    if not files:
        raise HTTPException(status_code=422, detail="Debes enviar al menos una imagen")
    ensure_media_directory()
    filenames: list[str] = []
    try:
        uploaded_media = [save_media(upload) for upload in files]
        filenames = [filename for filename, _, _ in uploaded_media]
        images = [GalleryImage(category_id=category.id, filename=filename, uploaded_by_id=user.id, media_type=media_type, duration_seconds=duration) for filename, media_type, duration in uploaded_media]
        db.add_all(images)
        db.commit()
        for image in images:
            db.refresh(image)
        return [image_response(image, request) for image in images]
    except Exception:
        db.rollback()
        for filename in filenames:
            try:
                (MEDIA_DIRECTORY / filename).unlink(missing_ok=True)
            except OSError:
                logger.exception("No se pudo eliminar el archivo temporal %s", filename)
        raise


def list_images(request: Request, db: Session, page: int, category_id: uuid.UUID | None) -> GalleryImagePage:
    filters = [] if category_id is None else [GalleryImage.category_id == category_id]
    total = db.scalar(select(func.count()).select_from(GalleryImage).where(*filters)) or 0
    images = list(db.scalars(select(GalleryImage).options(joinedload(GalleryImage.category), joinedload(GalleryImage.uploaded_by)).where(*filters).order_by(GalleryImage.created_at.desc(), GalleryImage.id.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)))
    return GalleryImagePage(items=[image_response(image, request) for image in images], total=total, page=page, page_size=PAGE_SIZE, total_pages=ceil(total / PAGE_SIZE) if total else 0)


def delete_image(image_id: uuid.UUID, db: Session) -> None:
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
