import io

import pytest
from fastapi import HTTPException, UploadFile

from app.models.categories import Category
from app.models.news import News
from app.models.users import User
from app.roles import Role
from app.schemas import CategoryCreate
from app.services import categories, gallery, news


def test_category_service_rejects_duplicate_name(db):
    categories.create_category(CategoryCreate(name="Arte"), db)

    with pytest.raises(HTTPException) as error:
        categories.create_category(CategoryCreate(name="Arte"), db)

    assert error.value.status_code == 409


def test_news_service_rejects_access_from_another_writer(db):
    category = Category(name="Arte")
    author = User(email="author@example.com", name="Author", role=Role.WRITER)
    other_writer = User(
        email="other@example.com", name="Other", role=Role.WRITER
    )
    db.add_all([category, author, other_writer])
    db.flush()
    article = News(
        title="Article",
        slug="article",
        category_id=category.id,
        author_id=author.id,
    )
    db.add(article)
    db.commit()

    with pytest.raises(HTTPException) as error:
        news.get_news_for_user(article.id, db, other_writer)

    assert error.value.status_code == 403


def test_gallery_service_removes_video_when_duration_is_invalid(tmp_path, monkeypatch):
    monkeypatch.setattr(gallery, "MEDIA_DIRECTORY", tmp_path)
    monkeypatch.setattr(gallery, "video_duration_seconds", lambda _: 10.0)
    upload = UploadFile(
        filename="promo.mp4",
        file=io.BytesIO(b"0" * (3 * 1024 * 1024)),
        headers={"content-type": "video/mp4"},
    )

    with pytest.raises(HTTPException) as error:
        gallery.save_promotional_video(upload)

    assert error.value.status_code == 422
    assert list(tmp_path.iterdir()) == []
