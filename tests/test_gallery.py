import io
import uuid

from fastapi import UploadFile
from PIL import Image

from app.services import gallery
from app.models.gallery import GalleryImage


def png_file() -> tuple[str, bytes, str]:
    buffer = io.BytesIO()
    Image.new("RGB", (12, 8), "red").save(buffer, format="PNG")
    return ("picture.png", buffer.getvalue(), "image/png")


def create_category(client, name="Arte"):
    response = client.post("/api/v1/categories", json={"name": name})
    assert response.status_code == 201
    return response.json()


def test_upload_converts_png_to_webp_and_publishes_url(client):
    category = create_category(client)
    name, content, content_type = png_file()

    response = client.post(
        "/api/v1/gallery/images",
        data={"category_id": category["id"]},
        files=[("files", (name, content, content_type))],
    )

    assert response.status_code == 201
    image = response.json()[0]
    assert image["url"].startswith("http://testserver/media/")
    assert image["uploaded_by_id"]
    assert image["uploaded_by_name"] == "Editor"
    saved_file = gallery.MEDIA_DIRECTORY / image["url"].rsplit("/", 1)[1]
    with Image.open(saved_file) as converted:
        assert converted.format == "WEBP"


def test_upload_rejects_invalid_file_and_duplicate_category(client):
    category = create_category(client)
    assert client.post("/api/v1/categories", json={"name": "Arte"}).status_code == 409

    response = client.post(
        "/api/v1/gallery/images",
        data={"category_id": category["id"]},
        files=[("files", ("bad.png", b"not-an-image", "image/png"))],
    )
    assert response.status_code == 422


def test_upload_video_requires_promotional_size_and_duration(client, monkeypatch):
    category = create_category(client)
    too_small = client.post(
        "/api/v1/gallery/images",
        data={"category_id": category["id"]},
        files=[("files", ("promo.mp4", b"small", "video/mp4"))],
    )
    assert too_small.status_code == 422

    monkeypatch.setattr(gallery, "video_duration_seconds", lambda _: 20.0)
    response = client.post(
        "/api/v1/gallery/images",
        data={"category_id": category["id"]},
        files=[("files", ("promo.mp4", b"0" * (3 * 1024 * 1024), "video/mp4"))],
    )
    assert response.status_code == 201
    video = response.json()[0]
    assert video["media_type"] == "video"
    assert video["duration_seconds"] == 20.0
    assert video["url"].endswith(".mp4")


def test_listing_is_public_paginated_and_can_filter_by_category(client, db):
    art = create_category(client, "Arte")
    other = create_category(client, "Fotografía")
    art_id = uuid.UUID(art["id"])
    other_id = uuid.UUID(other["id"])
    db.add_all(
        [
            GalleryImage(category_id=art_id, filename=f"art-{number}.webp")
            for number in range(11)
        ]
        + [GalleryImage(category_id=other_id, filename="other.webp")]
    )
    db.commit()

    first_page = client.get("/api/v1/gallery/images?page=1")
    assert first_page.status_code == 200
    assert first_page.json()["total"] == 12
    assert len(first_page.json()["items"]) == 10
    assert first_page.json()["total_pages"] == 2

    filtered = client.get(f"/api/v1/gallery/images?category_id={art['id']}&page=2")
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 11
    assert len(filtered.json()["items"]) == 1
    assert client.get("/api/v1/gallery/images?page=0").status_code == 422


def test_cannot_delete_category_with_images(client, db):
    category = create_category(client)
    db.add(
        GalleryImage(category_id=uuid.UUID(category["id"]), filename="protected.webp")
    )
    db.commit()

    response = client.delete(f"/api/v1/categories/{category['id']}")
    assert response.status_code == 409


def test_save_as_webp_rejects_unsupported_content_type(tmp_path, monkeypatch):
    monkeypatch.setattr(gallery, "MEDIA_DIRECTORY", tmp_path)
    upload = UploadFile(
        filename="text.txt",
        file=io.BytesIO(b"hello"),
        headers={"content-type": "text/plain"},
    )
    try:
        gallery.save_as_webp(upload)
    except Exception as exc:
        assert exc.status_code == 415
    else:
        raise AssertionError("Se esperaba que la carga fuera rechazada")
