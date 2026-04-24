from __future__ import annotations

from decimal import Decimal
from typing import Optional, List

from sqlalchemy import select, func, delete

from db.models import Grade, StudentModule
from .generic_dao import GenericDAOImp


class GradeDAOImp(GenericDAOImp[Grade, int]):
    def __init__(self, session):
        super().__init__(Grade, session)

    def find_by_student_module(self, student_module_id: int) -> List[Grade]:
        return list(
            self.session.scalars(
                select(Grade)
                .where(Grade.id_student_module == student_module_id)
                .order_by(Grade.id.desc())
            ).all()
        )

    def find_by_student(self, student_id: int) -> List[Grade]:
        return list(
            self.session.scalars(
                select(Grade)
                .join(StudentModule, Grade.id_student_module == StudentModule.id)
                .where(StudentModule.id_student == student_id)
                .order_by(Grade.id.desc())
            ).all()
        )

    def find_by_module(self, module_id: int) -> List[Grade]:
        return list(
            self.session.scalars(
                select(Grade)
                .join(StudentModule, Grade.id_student_module == StudentModule.id)
                .where(StudentModule.id_module == module_id)
                .order_by(Grade.id.desc())
            ).all()
        )

    def calculate_average_grade(self, student_module_id: int) -> Decimal:
        avg_val = self.session.scalar(
            select(func.avg(Grade.grade)).where(Grade.id_student_module == student_module_id)
        )
        return Decimal(str(avg_val)) if avg_val is not None else Decimal("0")

    def find_latest_grade(self, student_module_id: int) -> Optional[Grade]:
        return self.session.scalar(
            select(Grade)
            .where(Grade.id_student_module == student_module_id)
            .order_by(Grade.id.desc())
            .limit(1)
        )

    def find_highest_grade(self, student_module_id: int) -> Optional[Grade]:
        return self.session.scalar(
            select(Grade)
            .where(Grade.id_student_module == student_module_id)
            .order_by(Grade.grade.desc())
            .limit(1)
        )

    def find_lowest_grade(self, student_module_id: int) -> Optional[Grade]:
        return self.session.scalar(
            select(Grade)
            .where(Grade.id_student_module == student_module_id)
            .order_by(Grade.grade.asc())
            .limit(1)
        )

    def find_by_grade_range(self, min_grade: Decimal, max_grade: Decimal) -> List[Grade]:
        return list(
            self.session.scalars(
                select(Grade)
                .where(Grade.grade.between(min_grade, max_grade))
                .order_by(Grade.grade.desc())
            ).all()
        )

    def count_passed_by_module(self, module_id: int) -> int:
        cnt = self.session.scalar(
            select(func.count(func.distinct(Grade.id_student_module)))
            .join(StudentModule, Grade.id_student_module == StudentModule.id)
            .where(StudentModule.id_module == module_id, Grade.grade >= Decimal("5.0"))
        )
        return int(cnt or 0)

    def count_failed_by_module(self, module_id: int) -> int:
        cnt = self.session.scalar(
            select(func.count(func.distinct(Grade.id_student_module)))
            .join(StudentModule, Grade.id_student_module == StudentModule.id)
            .where(StudentModule.id_module == module_id, Grade.grade < Decimal("5.0"))
        )
        return int(cnt or 0)

    def has_passed(self, student_module_id: int, passing_grade: Decimal) -> bool:
        return self.calculate_average_grade(student_module_id) >= passing_grade

    def find_passed_grades_by_module(self, module_id: int) -> List[Grade]:
        return list(
            self.session.scalars(
                select(Grade)
                .join(StudentModule, Grade.id_student_module == StudentModule.id)
                .where(StudentModule.id_module == module_id, Grade.grade >= Decimal("5.0"))
                .order_by(Grade.grade.desc())
            ).all()
        )

    def find_failed_grades_by_module(self, module_id: int) -> List[Grade]:
        return list(
            self.session.scalars(
                select(Grade)
                .join(StudentModule, Grade.id_student_module == StudentModule.id)
                .where(StudentModule.id_module == module_id, Grade.grade < Decimal("5.0"))
                .order_by(Grade.grade.asc())
            ).all()
        )

    def calculate_overall_average_by_student(self, student_id: int) -> Decimal:
        avg_val = self.session.scalar(
            select(func.avg(Grade.grade))
            .join(StudentModule, Grade.id_student_module == StudentModule.id)
            .where(StudentModule.id_student == student_id)
        )
        return Decimal(str(avg_val)) if avg_val is not None else Decimal("0")

    def calculate_average_grade_by_module(self, module_id: int) -> Decimal:
        avg_val = self.session.scalar(
            select(func.avg(Grade.grade))
            .join(StudentModule, Grade.id_student_module == StudentModule.id)
            .where(StudentModule.id_module == module_id)
        )
        return Decimal(str(avg_val)) if avg_val is not None else Decimal("0")

    def count_by_student_module(self, student_module_id: int) -> int:
        cnt = self.session.scalar(
            select(func.count()).select_from(Grade).where(Grade.id_student_module == student_module_id)
        )
        return int(cnt or 0)

    def delete_by_student_module(self, student_module_id: int) -> None:
        self.session.execute(delete(Grade).where(Grade.id_student_module == student_module_id))
        self.session.flush()