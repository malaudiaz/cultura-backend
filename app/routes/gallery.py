import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.users import User
from app.roles import Role
from app.schemas import GalleryImagePage, GalleryImageResponse
from app.services import gallery as gallery_service


router = APIRouter(prefix="/gallery", tags=["galería"])
DbSession = Annotated[Session, Depends(get_db)]
Manager = Annotated[User, Depends(require_role(Role.ADMIN, Role.EDITOR))]
Uploader = Annotated[User, Depends(require_role(Role.ADMIN, Role.EDITOR, Role.WRITER))]


@router.post("/images", response_model=list[GalleryImageResponse], status_code=status.HTTP_201_CREATED)
def upload_images(request: Request, category_id: Annotated[uuid.UUID, Form()], files: Annotated[list[UploadFile], File()], db: DbSession, user: Uploader) -> list[GalleryImageResponse]:
    return gallery_service.upload_images(request, category_id, files, db, user)


@router.get("/images", response_model=GalleryImagePage)
def list_images(request: Request, db: DbSession, page: Annotated[int, Query(ge=1)] = 1, category_id: uuid.UUID | None = None) -> GalleryImagePage:
    return gallery_service.list_images(request, db, page, category_id)


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(image_id: uuid.UUID, db: DbSession, _: Manager) -> None:
    gallery_service.delete_image(image_id, db)
