from __future__ import annotations

from typing import Optional, List

from sqlalchemy import select, func

from db.models import Module, Teacher, Student, StudentModule
from .generic_dao import GenericDAOImp


class ModuleDAOImp(GenericDAOImp[Module, int]):
    def __init__(self, session):
        super().__init__(Module, session)

    def find_by_module_name(self, module_name: str) -> List[Module]:
        term = f"%{module_name.lower()}%"
        return list(self.session.scalars(select(Module).where(func.lower(Module.module_name).like(term))).all())

    def find_by_module_name_exact(self, module_name: str) -> Optional[Module]:
        return self.session.scalar(select(Module).where(Module.module_name == module_name))

    def find_by_course(self, course: str) -> List[Module]:
        return list(self.session.scalars(select(Module).where(Module.course == course)).all())

    def get_teachers_by_module(self, module_id: int) -> List[Teacher]:
        return list(self.session.scalars(select(Teacher).join(Teacher.modules).where(Module.id == module_id)).all())

    def get_students_by_module(self, module_id: int) -> List[Student]:
        return list(
            self.session.scalars(
                select(Student)
                .join(StudentModule, StudentModule.id_student == Student.id)
                .where(StudentModule.id_module == module_id)
            ).all()
        )

    def count_students_by_module(self, module_id: int) -> int:
        cnt = self.session.scalar(
            select(func.count()).select_from(StudentModule).where(StudentModule.id_module == module_id)
        )
        return int(cnt or 0)

    def count_teachers_by_module(self, module_id: int) -> int:
        cnt = self.session.scalar(
            select(func.count()).select_from(Teacher).join(Teacher.modules).where(Module.id == module_id)
        )
        return int(cnt or 0)

    def find_by_teacher(self, teacher_id: int) -> List[Module]:
        return list(self.session.scalars(select(Module).join(Module.teachers).where(Teacher.id == teacher_id)).all())

    def find_by_student(self, student_id: int) -> List[Module]:
        return list(
            self.session.scalars(
                select(Module)
                .join(StudentModule, StudentModule.id_module == Module.id)
                .where(StudentModule.id_student == student_id)
            ).all()
        )

    def find_by_semanal_hours_range(self, min_hours: int, max_hours: int) -> List[Module]:
        return list(self.session.scalars(select(Module).where(Module.semanal_hours.between(min_hours, max_hours))).all())

    def find_all_courses(self) -> List[str]:
        return list(self.session.scalars(select(Module.course).distinct().order_by(Module.course)).all())

    def exists_by_module_name(self, module_name: str) -> bool:
        cnt = self.session.scalar(select(func.count()).select_from(Module).where(Module.module_name == module_name))
        return (cnt or 0) > 0