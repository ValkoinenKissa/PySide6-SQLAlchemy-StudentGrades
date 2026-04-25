from __future__ import annotations

from typing import Optional, List

from sqlalchemy import select, func

from db.models import Student, Module, StudentModule
from .generic_dao import GenericDAOImp


class StudentDAOImp(GenericDAOImp[Student, int]):
    def __init__(self, session):
        super().__init__(Student, session)

    def find_by_user_id(self, user_id: int) -> Optional[Student]:
        return self.session.scalar(select(Student).where(Student.id_user == user_id))

    def find_by_course(self, course: str) -> List[Student]:
        return list(self.session.scalars(select(Student).where(Student.course == course)).all())

    def find_by_grade_group(self, grade_group: str) -> List[Student]:
        return list(self.session.scalars(select(Student).where(Student.grade_group == grade_group)).all())

    def find_by_course_and_grade_group(self, course: str, grade_group: str) -> List[Student]:
        return list(
            self.session.scalars(
                select(Student).where(Student.course == course, Student.grade_group == grade_group)
            ).all()
        )

    def get_modules_by_student(self, student_id: int) -> List[Module]:
        return list(
            self.session.scalars(
                select(Module)
                .join(StudentModule, StudentModule.id_module == Module.id)
                .where(StudentModule.id_student == student_id)
            ).all()
        )

    def get_enrollments_by_student(self, student_id: int) -> List[StudentModule]:
        return list(self.session.scalars(select(StudentModule).where(StudentModule.id_student == student_id)).all())

    def find_by_module(self, module_id: int) -> List[Student]:
        return list(
            self.session.scalars(
                select(Student)
                .join(StudentModule, StudentModule.id_student == Student.id)
                .where(StudentModule.id_module == module_id)
            ).all()
        )

    def is_enrolled_in_module(self, student_id: int, module_id: int) -> bool:
        cnt = self.session.scalar(
            select(func.count()).select_from(StudentModule).where(
                StudentModule.id_student == student_id,
                StudentModule.id_module == module_id,
            )
        )
        return (cnt or 0) > 0

    def count_modules_by_student(self, student_id: int) -> int:
        cnt = self.session.scalar(
            select(func.count()).select_from(StudentModule).where(StudentModule.id_student == student_id)
        )
        return int(cnt or 0)

    def find_all_courses(self) -> List[str]:
        return list(self.session.scalars(select(Student.course).distinct().order_by(Student.course)).all())

    def find_all_grade_groups(self) -> List[str]:
        return list(self.session.scalars(select(Student.grade_group).distinct().order_by(Student.grade_group)).all())