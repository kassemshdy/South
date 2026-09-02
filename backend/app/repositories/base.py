"""Repository base.

Repositories are the only place that talks to the ORM. They never make
authorization decisions — that belongs to services and API dependencies — so a
repository method can be reused safely from both owner and admin code paths.
"""

from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, entity_id: uuid.UUID) -> ModelT | None:
        return self.db.get(self.model, entity_id)

    def add(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        self.db.flush()
        return entity

    def delete(self, entity: ModelT) -> None:
        self.db.delete(entity)
        self.db.flush()

    def count(self) -> int:
        return int(
            self.db.execute(select(func.count()).select_from(self.model)).scalar_one()
        )
