import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


TEST_DATABASE = Path("/tmp/cultura-gallery-tests.db")
TEST_MEDIA = Path("/tmp/cultura-gallery-media")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE}"
os.environ["IMAGE_STORAGE_PATH"] = str(TEST_MEDIA)

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.dependencies import get_current_user  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.roles import Role  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    shutil.rmtree(TEST_MEDIA, ignore_errors=True)
    TEST_MEDIA.mkdir(parents=True)
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    manager = User(email="editor@example.com", name="Editor", role=Role.EDITOR)
    with SessionLocal() as db:
        db.add(manager)
        db.commit()
        db.refresh(manager)
        manager_id = manager.id

    def current_manager():
        with SessionLocal() as db:
            return db.get(User, manager_id)

    app.dependency_overrides[get_current_user] = current_manager
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session
