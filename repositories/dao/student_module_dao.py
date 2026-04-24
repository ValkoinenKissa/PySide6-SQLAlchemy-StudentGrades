from __future__ import annotations

from decimal import Decimal
from typing import Optional, List

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from db.models import StudentModule, Student, Module, Grade
from .generic_dao import GenericDAOImp


class StudentModuleDAOImp(GenericDAOImp[StudentModule, int]):
    def __init__(self, session):
        super().__init__(StudentModule, session)

    def find_by_student_and_module(self, student_id: int, module_id: int) -> Optional[StudentModule]:
        return self.session.scalar(
            select(StudentModule).where(
                StudentModule.id_student == student_id,
                StudentModule.id_module == module_id,
            )
        )

    def find_by_student(self, student_id: int) -> List[StudentModule]:
        return list(self.session.scalars(select(StudentModule).where(StudentModule.id_student == student_id)).all())

    def find_by_module(self, module_id: int) -> List[StudentModule]:
        return list(self.session.scalars(select(StudentModule).where(StudentModule.id_module == module_id)).all())

    def get_grades_by_enrollment(self, student_module_id: int) -> List[Grade]:
        return list(
            self.session.scalars(
                select(Grade)
                .where(Grade.id_student_module == student_module_id)
                .order_by(Grade.id.desc())
            ).all()
        )

    def exists_enrollment(self, student_id: int, module_id: int) -> bool:
        cnt = self.session.scalar(
            select(func.count()).select_from(StudentModule).where(
                StudentModule.id_student == student_id,
                StudentModule.id_module == module_id,
            )
        )
        return (cnt or 0) > 0

    def enroll_student(self, student_id: int, module_id: int) -> StudentModule:
        student = self.session.get(Student, student_id)
        module = self.session.get(Module, module_id)
        if not student:
            raise RuntimeError(f"Estudiante no encontrado con ID: {student_id}")
        if not module:
            raise RuntimeError(f"Módulo no encontrado con ID: {module_id}")

        enrollment = StudentModule(id_student=student_id, id_module=module_id)
        self.session.add(enrollment)
        self.session.flush()
        return enrollment

    def unenroll_student(self, student_id: int, module_id: int) -> None:
        enrollment = self.find_by_student_and_module(student_id, module_id)
        if enrollment:
            self.session.delete(enrollment)
            self.session.flush()

    def find_by_student_with_grades(self, student_id: int) -> List[StudentModule]:
        return list(
            self.session.scalars(
                select(StudentModule)
                .options(selectinload(StudentModule.grades))
                .where(StudentModule.id_student == student_id)
            ).all()
        )

    def calculate_average_grade(self, student_module_id: int) -> Decimal:
        avg_val = self.session.scalar(
            select(func.avg(Grade.grade)).where(Grade.id_student_module == student_module_id)
        )
        return Decimal(str(avg_val)) if avg_val is not None else Decimal("0")

    def find_by_id_with_grades(self, student_module_id: int) -> Optional[StudentModule]:
        return self.session.scalar(
            select(StudentModule)
            .options(selectinload(StudentModule.grades))
            .where(StudentModule.id == student_module_id)
        )

    def count_by_student(self, student_id: int) -> int:
        cnt = self.session.scalar(
            select(func.count()).select_from(StudentModule).where(StudentModule.id_student == student_id)
        )
        return int(cnt or 0)

    def count_by_module(self, module_id: int) -> int:
        cnt = self.session.scalar(
            select(func.count()).select_from(StudentModule).where(StudentModule.id_module == module_id)
        )
        return int(cnt or 0)