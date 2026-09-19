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
from app.core.phone import normalize_phone
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
def category_other(db: Session) -> Category:
    """The seeded "Other" category — real slug, since that's the sentinel
    the app looks for, not a NULL category_id."""
    entity = Category(name_ar=ar("category.other"), slug="other", sort_order=99)
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


#: The password every account this helper makes is given. A fixed value is
#: right here for the same reason it would be wrong anywhere else: these
#: accounts exist for the length of one test.
OWNER_PASSWORD = "TestOwner!123"

#: Hashed once, not per account. bcrypt is deliberately slow, and the suite
#: creates hundreds of owners — hashing the same string each time spends
#: minutes proving something bcrypt's own tests already prove.
_OWNER_PASSWORD_HASH = hash_password(OWNER_PASSWORD)


def make_owner(phone: str, **fields: object) -> User:
    """An owner account with a password, created directly.

    Signing in no longer creates an account — an administrator does, by
    approving an application and issuing credentials — so a test that needs an
    owner has to make one. Direct rather than through the registration
    endpoint, because most tests want an owner, not an application: the
    registration route's own behaviour is `tests/test_registration.py`.
    """
    session = SessionLocal()
    try:
        user = User(
            phone_number=normalize_phone(phone),
            role=UserRole.OWNER,
            password_hash=_OWNER_PASSWORD_HASH,
            **fields,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user
    finally:
        session.close()


def sign_in(client: TestClient, phone: str) -> dict[str, str]:
    """An auth header for ``phone``, creating the account if it is new."""
    normalized = normalize_phone(phone)
    session = SessionLocal()
    try:
        existing = (
            session.query(User).filter(User.phone_number == normalized).one_or_none()
        )
    finally:
        session.close()
    if existing is None:
        make_owner(normalized)

    response = client.post(
        "/api/auth/login", json={"identifier": phone, "password": OWNER_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def admin_headers(client: TestClient, email: str = "admin@example.com") -> dict[str, str]:
    response = client.post(
        "/api/auth/admin/login", json={"email": email, "password": "AdminPass!123"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
