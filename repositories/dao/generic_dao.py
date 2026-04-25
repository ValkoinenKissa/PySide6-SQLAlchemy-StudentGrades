from __future__ import annotations

from typing import Generic, Optional, TypeVar, Type, List

from sqlalchemy import select, func
from sqlalchemy.orm import Session

T = TypeVar("T")
ID = TypeVar("ID")


class GenericDAOImp(Generic[T, ID]):
    def __init__(self, entity_class: Type[T], session: Session):
        self.entity_class = entity_class
        self.session = session

    def save(self, entity: T) -> None:
        self.session.add(entity)
        self.session.flush()

    def update(self, entity: T) -> T:
        merged = self.session.merge(entity)
        self.session.flush()
        return merged

    def save_or_update(self, entity: T) -> T:
        merged = self.session.merge(entity)
        self.session.flush()
        return merged

    def delete(self, entity: T) -> None:
        self.session.delete(entity)
        self.session.flush()

    def delete_by_id(self, id_: ID) -> None:
        entity = self.find_by_id(id_)
        if entity is not None:
            self.session.delete(entity)
            self.session.flush()

    def find_by_id(self, id_: ID) -> Optional[T]:
        return self.session.get(self.entity_class, id_)

    def find_all(self) -> List[T]:
        return list(self.session.scalars(select(self.entity_class)).all())

    def count(self) -> int:
        return int(self.session.scalar(select(func.count()).select_from(self.entity_class)) or 0)

    def exists_by_id(self, id_: ID) -> bool:
        stmt = select(func.count()).select_from(self.entity_class).where(self.entity_class.id == id_)  # type: ignore[attr-defined]
        return (self.session.scalar(stmt) or 0) > 0