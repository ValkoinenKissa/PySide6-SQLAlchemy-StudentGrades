from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    String,
    Integer,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    Enum as SAEnum,
    Table,
    Column,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ===== Enum =====
class UserType(str, Enum):
    ESTUDIANTE = "ESTUDIANTE"
    PROFESOR = "PROFESOR"


# ===== Tabla intermedia N:M Teacher <-> Module =====
teacher_module = Table(
    "teacher_module",
    Base.metadata,
    Column("teacher_id", ForeignKey("teachers.id"), primary_key=True),
    Column("module_id", ForeignKey("modules.id"), primary_key=True),
)


# ===== Models =====
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[Optional[str]] = mapped_column(String, unique=True)
    password_hash: Mapped[Optional[str]] = mapped_column("password_hash", String)
    first_name: Mapped[Optional[str]] = mapped_column("first_name", String)
    last_name: Mapped[Optional[str]] = mapped_column("last_name", String)
    user_type: Mapped[Optional[UserType]] = mapped_column(
        "user_type", SAEnum(UserType, name="user_type", native_enum=False)
    )

    # 1:1 inversas (mappedBy = "user")
    teacher: Mapped[Optional["Teacher"]] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    student: Mapped[Optional["Student"]] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    department: Mapped[Optional[str]] = mapped_column(String(100))
    specialty: Mapped[Optional[str]] = mapped_column(String(100))

    id_user: Mapped[int] = mapped_column(
        "id_user", ForeignKey("users.id"), unique=True, nullable=False
    )
    user: Mapped["User"] = relationship(back_populates="teacher")

    # N:M con Module
    modules: Mapped[List["Module"]] = relationship(
        secondary=teacher_module,
        back_populates="teachers",
        lazy="select",
    )


class Student(Base):
    __tablename__ = "student"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course: Mapped[Optional[str]] = mapped_column(String(50))
    grade_group: Mapped[Optional[str]] = mapped_column("grade_group", String(10))

    id_user: Mapped[int] = mapped_column(
        "id_user", ForeignKey("users.id"), unique=True, nullable=False
    )
    user: Mapped["User"] = relationship(back_populates="student")

    # 1:N con StudentModule
    enrollments: Mapped[List["StudentModule"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        lazy="select",
    )


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_name: Mapped[Optional[str]] = mapped_column("module_name", String(150))
    course: Mapped[Optional[str]] = mapped_column(String(50))
    semanal_hours: Mapped[Optional[int]] = mapped_column("semanal_hours", Integer)

    # N:M inversa con Teacher
    teachers: Mapped[List["Teacher"]] = relationship(
        secondary=teacher_module,
        back_populates="modules",
        lazy="select",
    )

    # 1:N con StudentModule
    enrollments: Mapped[List["StudentModule"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan",
        lazy="select",
    )


class StudentModule(Base):
    __tablename__ = "student_module"
    __table_args__ = (
        UniqueConstraint("id_student", "id_module", name="uq_student_module_student_module"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    id_student: Mapped[int] = mapped_column(
        "id_student", ForeignKey("student.id"), nullable=False
    )
    id_module: Mapped[int] = mapped_column(
        "id_module", ForeignKey("modules.id"), nullable=False
    )

    # En Hibernate estaba EAGER; aquí lo puedes dejar como "joined" para emularlo
    student: Mapped["Student"] = relationship(back_populates="enrollments", lazy="joined")
    module: Mapped["Module"] = relationship(back_populates="enrollments", lazy="joined")

    grades: Mapped[List["Grade"]] = relationship(
        back_populates="student_module",
        cascade="all, delete-orphan",
        lazy="select",
    )


class Grade(Base):
    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    grade: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2))
    notes: Mapped[Optional[str]] = mapped_column(String(500))

    id_student_module: Mapped[int] = mapped_column(
        "id_student_module", ForeignKey("student_module.id"), nullable=False
    )
    student_module: Mapped["StudentModule"] = relationship(
        back_populates="grades",
        lazy="select",
    )