"""Datos de desarrollo idempotentes; ejecutar con ``python -m app.seed``."""

import os
from datetime import date

from sqlalchemy import select

from app.database import SessionLocal
from app.models.categories import Category
from app.models.news import News, NewsRevision, NewsSection, NewsTag, Tag
from app.models.users import User
from app.roles import Role
from app.security import hash_password


def seed() -> None:
    password = os.getenv("SEED_ADMIN_PASSWORD", "change-me")
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == "admin@cultura.local"))
        if not admin:
            admin = User(email="admin@cultura.local", name="Administrator", role=Role.ADMIN, password_hash=hash_password(password))
            db.add(admin)
        writer = db.scalar(select(User).where(User.email == "writer@cultura.local"))
        if not writer:
            writer = User(email="writer@cultura.local", name="Sample Writer", role=Role.WRITER, password_hash=hash_password(password))
            db.add(writer)
        category = db.scalar(select(Category).where(Category.name == "Visual Arts"))
        if not category:
            category = Category(name="Visual Arts")
            db.add(category)
        tags = []
        for name in ("Featured", "Community"):
            tag = db.scalar(select(Tag).where(Tag.name == name))
            if not tag:
                tag = Tag(name=name)
                db.add(tag)
            tags.append(tag)
        db.flush()
        if not db.scalar(select(News).where(News.slug == "welcome-to-cultura")):
            db.add(News(title="Welcome to Cultura", slug="welcome-to-cultura", category=category, author=writer, editor=admin, status="published", featured=True, publication_date=date.today(), summary="Sample content.", sections=[NewsSection(title="Culture for everyone", content="Editorial models are ready.", element_order=["title", "content"], position=0)], tag_links=[NewsTag(tag=tag) for tag in tags], revisions=[NewsRevision(editor=admin, action="published", notes="Created by seed.")]))
        db.commit()


if __name__ == "__main__":
    seed()
