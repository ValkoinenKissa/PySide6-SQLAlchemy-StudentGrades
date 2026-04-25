from __future__ import annotations

from typing import Optional, List

from sqlalchemy import select, func

from db.models import Teacher, Module
from .generic_dao import GenericDAOImp


class TeacherDAOImp(GenericDAOImp[Teacher, int]):
    def __init__(self, session):
        super().__init__(Teacher, session)

    def find_by_user_id(self, user_id: int) -> Optional[Teacher]:
        return self.session.scalar(select(Teacher).where(Teacher.id_user == user_id))

    def find_by_department(self, department: str) -> List[Teacher]:
        return list(self.session.scalars(select(Teacher).where(Teacher.department == department)).all())

    def find_by_specialty(self, specialty: str) -> List[Teacher]:
        return list(self.session.scalars(select(Teacher).where(Teacher.specialty == specialty)).all())

    def get_modules_by_teacher(self, teacher_id: int) -> List[Module]:
        return list(self.session.scalars(select(Module).join(Module.teachers).where(Teacher.id == teacher_id)).all())

    def find_by_module(self, module_id: int) -> List[Teacher]:
        return list(self.session.scalars(select(Teacher).join(Teacher.modules).where(Module.id == module_id)).all())

    def teaches_module(self, teacher_id: int, module_id: int) -> bool:
        cnt = self.session.scalar(
            select(func.count()).select_from(Teacher).join(Teacher.modules).where(
                Teacher.id == teacher_id, Module.id == module_id
            )
        )
        return (cnt or 0) > 0

    def assign_module(self, teacher_id: int, module_id: int) -> None:
        teacher = self.session.get(Teacher, teacher_id)
        module = self.session.get(Module, module_id)
        if not teacher or not module:
            raise RuntimeError("Profesor o módulo no encontrado")
        if module not in teacher.modules:
            teacher.modules.append(module)
            self.session.flush()

    def unassign_module(self, teacher_id: int, module_id: int) -> None:
        teacher = self.session.get(Teacher, teacher_id)
        if not teacher:
            return

        module_to_remove = next((m for m in teacher.modules if m.id == module_id), None)
        if module_to_remove is not None:
            teacher.modules.remove(module_to_remove)

        self.session.flush()

    def count_modules_by_teacher(self, teacher_id: int) -> int:
        cnt = self.session.scalar(
            select(func.count(Module.id)).select_from(Module).join(Module.teachers).where(Teacher.id == teacher_id)
        )
        return int(cnt or 0)