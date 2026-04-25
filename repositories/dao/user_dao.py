from __future__ import annotations

from typing import Optional, List

from sqlalchemy import select, func

from db.models import User, UserType
from .generic_dao import GenericDAOImp


class UserDAOImp(GenericDAOImp[User, int]):
    def __init__(self, session):
        super().__init__(User, session)

    def find_by_username(self, username: str) -> Optional[User]:
        return self.session.scalar(select(User).where(User.username == username))

    def validate_login(self, username: str, password_hash: str) -> Optional[User]:
        return self.session.scalar(
            select(User).where(User.username == username, User.password_hash == password_hash)
        )

    def find_by_user_type(self, user_type: UserType) -> List[User]:
        return list(self.session.scalars(select(User).where(User.user_type == user_type)).all())

    def exists_username(self, username: str) -> bool:
        cnt = self.session.scalar(select(func.count()).select_from(User).where(User.username == username))
        return (cnt or 0) > 0

    def search_by_name(self, search_term: str) -> List[User]:
        term = f"%{search_term.lower()}%"
        return list(
            self.session.scalars(
                select(User).where(
                    func.lower(User.first_name).like(term) | func.lower(User.last_name).like(term)
                )
            ).all()
        )

    def change_password(self, user_id: int, new_password_hash: str) -> None:
        user = self.session.get(User, user_id)
        if not user:
            raise RuntimeError(f"Usuario no encontrado con ID: {user_id}")
        user.password_hash = new_password_hash
        self.session.flush()