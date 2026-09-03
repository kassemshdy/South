"""Test fixtures.

Each test runs against a real PostgreSQL database (the same engine used in
production) rather than SQLite, so enum handling, trigram search and cascade
behaviour are exercised as they actually ship.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/south_test"
)
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("STORAGE_LOCAL_DIR", "var/test-media")

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.main import create_app
from app.models.enums import LocationType, UserRole
from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.samples import ar


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean_tables() -> Iterator[None]:
    """Truncate between tests so each one starts from a known state."""
    yield
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))


@pytest.fixture
def db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app(get_settings())) as test_client:
        yield test_client


@pytest.fixture
def category(db: Session) -> Category:
    entity = Category(
        name_ar=ar("category.restaurants"),
        slug=f"restaurants-{uuid.uuid4().hex[:6]}",
        sort_order=1,
    )
    db.add(entity)
    db.commit()
    return entity


@pytest.fixture
def location(db: Session) -> Location:
    entity = Location(
        name_ar=ar("location.tyre"),
        slug=f"tyre-{uuid.uuid4().hex[:6]}",
        type=LocationType.DISTRICT,
    )
    db.add(entity)
    db.commit()
    return entity


@pytest.fixture
def admin(db: Session) -> User:
    entity = User(
        email="admin@example.com",
        password_hash=hash_password("AdminPass!123"),
        display_name=ar("user.admin_name"),
        role=UserRole.ADMIN,
    )
    db.add(entity)
    db.commit()
    return entity


def sign_in(client: TestClient, phone: str) -> dict[str, str]:
    """Complete the OTP flow and return an auth header for ``phone``."""
    response = client.post("/api/auth/request-otp", json={"phone_number": phone})
    assert response.status_code == 200, response.text
    code = response.json()["debug_code"]
    assert code is not None

    verified = client.post("/api/auth/verify-otp", json={"phone_number": phone, "code": code})
    assert verified.status_code == 200, verified.text
    return {"Authorization": f"Bearer {verified.json()['access_token']}"}


def admin_headers(client: TestClient, email: str = "admin@example.com") -> dict[str, str]:
    response = client.post(
        "/api/auth/admin/login", json={"email": email, "password": "AdminPass!123"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
