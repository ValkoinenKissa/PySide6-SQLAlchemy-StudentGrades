from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PyQt6 import uic
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QComboBox,
    QLineEdit,
    QTableWidget,
    QPushButton,
    QMessageBox,
    QTableWidgetItem,
)

from db.database import get_session
from db.models import Grade
from dao.teacher_dao import TeacherDAOImp
from dao.student_module_dao import StudentModuleDAOImp
from dao.grade_dao import GradeDAOImp
from dao.user_dao import UserDAOImp

BASE_DIR = Path(__file__).resolve().parent.parent
UI_PATH = BASE_DIR / "ui" / "teacher-view.ui"


@dataclass
class StudentModuleRow:
    enrollment_id: int
    student_name: str
    course: str
    group: str
    last_grade: str
    avg_grade: str
    grade_count: str


@dataclass
class GradeRow:
    grade_id: int
    grade_value: str
    notes: str


class TeacherWindow(QWidget):
    if TYPE_CHECKING:
        lblTeacherTitle: QLabel
        lblSelectedStudent: QLabel
        comboModuleFilter: QComboBox
        editStudentSearch: QLineEdit
        summaryTable: QTableWidget
        lblGradesStudentName: QLabel
        editGradeValue: QLineEdit
        editGradeNotes: QLineEdit
        gradesHistoryTable: QTableWidget
        btnSaveGrade: QPushButton
        btnUpdateGrade: QPushButton
        btnClearGrade: QPushButton
        btnDeleteGrade: QPushButton
        btnLogout: QPushButton
        btnRefresh: QPushButton

    def __init__(self, user_id: int):
        super().__init__()
        uic.loadUi(str(UI_PATH), self)
        self.setFixedSize(self.size())

        self.user_id = user_id
        self.current_teacher_id: Optional[int] = None
        self.selected_row: Optional[StudentModuleRow] = None
        self.editing_grade_id: Optional[int] = None

        self.master_rows: list[StudentModuleRow] = []
        self.filtered_rows: list[StudentModuleRow] = []

        self._loading = False

        self._setup_tables()
        self._setup_signals()
        self._init_data()

    # Configuración de las tablas
    def _setup_tables(self) -> None:
        # Resumen alumnos
        self.summaryTable.setColumnCount(6)
        self.summaryTable.setHorizontalHeaderLabels(
            ["Alumno/a", "Curso", "Grupo", "Última", "Media", "Notas"]
        )
        self.summaryTable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.summaryTable.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.summaryTable.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Historial notas
        self.gradesHistoryTable.setColumnCount(2)
        self.gradesHistoryTable.setHorizontalHeaderLabels(["Nota", "Observaciones"])
        self.gradesHistoryTable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.gradesHistoryTable.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.gradesHistoryTable.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Estado inicial botones
        self.btnUpdateGrade.setEnabled(False)
        self.btnDeleteGrade.setEnabled(False)
        self.btnClearGrade.setEnabled(False)

    def _setup_signals(self) -> None:
        self.btnLogout.clicked.connect(self._handle_logout)
        self.btnRefresh.clicked.connect(self._load_students_for_selected_module)

        self.comboModuleFilter.currentIndexChanged.connect(self._on_module_changed)
        self.editStudentSearch.textChanged.connect(self._filter_students)

        self.summaryTable.itemSelectionChanged.connect(self._on_student_selected)
        self.gradesHistoryTable.itemSelectionChanged.connect(self._on_grade_selected)

        self.btnSaveGrade.clicked.connect(self._handle_save_grade)
        self.btnUpdateGrade.clicked.connect(self._handle_update_grade)
        self.btnDeleteGrade.clicked.connect(self._handle_delete_selected_grade)
        self.btnClearGrade.clicked.connect(self._handle_delete_all_grades)

    # ---------- init ----------
    def _init_data(self) -> None:
        try:
            with get_session() as session:
                user_dao = UserDAOImp(session)
                teacher_dao = TeacherDAOImp(session)

                user = user_dao.find_by_id(self.user_id)
                if user is None:
                    self._show_error("Usuario no encontrado")
                    return

                teacher = teacher_dao.find_by_user_id(self.user_id)
                if teacher is None:
                    self._show_error("No se encontraron datos de profesor")
                    return

                self.current_teacher_id = teacher.id
                self.lblSelectedStudent.setText(f"Profesor/a: {user.first_name} {user.last_name}")

            self._load_teacher_modules()

        except Exception as e:
            self._show_error(f"Error al inicializar profesor: {e}")

    # ---------- modules/students ----------
    def _load_teacher_modules(self) -> None:
        if self.current_teacher_id is None:
            return

        try:
            with get_session() as session:
                teacher_dao = TeacherDAOImp(session)
                modules = teacher_dao.get_modules_by_teacher(self.current_teacher_id)

            self._loading = True
            self.comboModuleFilter.clear()
            for m in modules:
                self.comboModuleFilter.addItem(m.module_name or "-", m.id)
            self._loading = False

            if modules:
                self.comboModuleFilter.setCurrentIndex(0)
                self._load_students_for_selected_module()
            else:
                self.summaryTable.setRowCount(0)

        except Exception as e:
            self._show_error(f"Error al cargar módulos: {e}")

    def _on_module_changed(self) -> None:
        if self._loading:
            return
        self._load_students_for_selected_module()

    def _load_students_for_selected_module(self) -> None:
        module_id = self.comboModuleFilter.currentData()
        if module_id is None:
            self.summaryTable.setRowCount(0)
            return

        try:
            with get_session() as session:
                sm_dao = StudentModuleDAOImp(session)
                grade_dao = GradeDAOImp(session)

                enrollments = sm_dao.find_by_module(module_id)
                rows: list[StudentModuleRow] = []

                for enrollment in enrollments:
                    student = enrollment.student
                    student_name = f"{student.user.first_name} {student.user.last_name}"

                    grades = grade_dao.find_by_student_module(enrollment.id)
                    grade_count = str(len(grades))
                    last_grade = "-"
                    avg_grade = "-"

                    if grades:
                        latest = grades[0]  # asumiendo orden desc
                        last_grade = f"{latest.grade:.2f}"

                        avg = grade_dao.calculate_average_grade(enrollment.id)
                        if avg is not None:
                            avg_grade = f"{avg:.2f}"

                    rows.append(
                        StudentModuleRow(
                            enrollment_id=enrollment.id,
                            student_name=student_name,
                            course=student.course or "-",
                            group=student.grade_group or "-",
                            last_grade=last_grade,
                            avg_grade=avg_grade,
                            grade_count=grade_count,
                        )
                    )

            self.master_rows = rows
            self._render_students(rows)

            self.selected_row = None
            self.lblGradesStudentName.setText("-")
            self.gradesHistoryTable.setRowCount(0)
            self.btnClearGrade.setEnabled(False)
            self.btnDeleteGrade.setEnabled(False)
            self.btnUpdateGrade.setEnabled(False)
            self.editing_grade_id = None

        except Exception as e:
            self._show_error(f"Error al cargar alumnos: {e}")

    def _render_students(self, rows: list[StudentModuleRow]) -> None:
        self.filtered_rows = rows
        self.summaryTable.setRowCount(len(rows))

        for i, row in enumerate(rows):
            self.summaryTable.setItem(i, 0, QTableWidgetItem(row.student_name))
            self.summaryTable.setItem(i, 1, QTableWidgetItem(row.course))
            self.summaryTable.setItem(i, 2, QTableWidgetItem(row.group))
            self.summaryTable.setItem(i, 3, QTableWidgetItem(row.last_grade))
            self.summaryTable.setItem(i, 4, QTableWidgetItem(row.avg_grade))
            self.summaryTable.setItem(i, 5, QTableWidgetItem(row.grade_count))

        self.summaryTable.resizeColumnsToContents()

    def _filter_students(self, text: str) -> None:
        q = (text or "").strip().lower()
        if not q:
            self._render_students(self.master_rows)
            return

        filtered = [r for r in self.master_rows if q in r.student_name.lower()]
        self._render_students(filtered)

    # filtrado por estudiante seleccionado
    def _on_student_selected(self) -> None:
        row_idx = self.summaryTable.currentRow()
        if row_idx < 0 or row_idx >= len(self.filtered_rows):
            return

        row = self.filtered_rows[row_idx]
        self.selected_row = row
        self.lblGradesStudentName.setText(row.student_name)

        self.editing_grade_id = None
        self.btnUpdateGrade.setEnabled(False)
        self.btnDeleteGrade.setEnabled(False)
        self.btnClearGrade.setEnabled(True)

        self._load_grades_history(row.enrollment_id)

    def _load_grades_history(self, enrollment_id: int) -> None:
        try:
            with get_session() as session:
                grade_dao = GradeDAOImp(session)
                grades = grade_dao.find_by_student_module(enrollment_id)

            self.gradesHistoryTable.setRowCount(len(grades))

            for i, g in enumerate(grades):
                val = f"{g.grade:.2f}"
                notes = g.notes or ""
                grade_item = QTableWidgetItem(val)
                grade_item.setData(0x0100, g.id)  # Qt.UserRole
                self.gradesHistoryTable.setItem(i, 0, grade_item)
                self.gradesHistoryTable.setItem(i, 1, QTableWidgetItem(notes))

            self.gradesHistoryTable.resizeColumnsToContents()
            self.btnDeleteGrade.setEnabled(False)

        except Exception as e:
            self._show_error(f"Error cargando historial: {e}")

    def _on_grade_selected(self) -> None:
        row_idx = self.gradesHistoryTable.currentRow()
        if row_idx < 0:
            self.editing_grade_id = None
            self.btnUpdateGrade.setEnabled(False)
            self.btnDeleteGrade.setEnabled(False)
            return

        item_grade = self.gradesHistoryTable.item(row_idx, 0)
        item_notes = self.gradesHistoryTable.item(row_idx, 1)
        if item_grade is None:
            return

        grade_id = item_grade.data(0x0100)
        self.editing_grade_id = int(grade_id) if grade_id is not None else None

        self.editGradeValue.setText(item_grade.text().replace(",", "."))
        self.editGradeNotes.setText(item_notes.text() if item_notes else "")

        self.btnUpdateGrade.setEnabled(self.editing_grade_id is not None)
        self.btnDeleteGrade.setEnabled(self.editing_grade_id is not None)

    # ---------- CRUD grades ----------
    def _parse_grade(self) -> Optional[Decimal]:
        raw = self.editGradeValue.text().strip().replace(",", ".")
        if not raw:
            self._warn("Debes introducir una nota")
            self.editGradeValue.setFocus()
            return None
        try:
            val = Decimal(raw)
        except InvalidOperation:
            self._warn("La nota debe ser un número válido")
            self.editGradeValue.setFocus()
            return None
        if val < Decimal("0") or val > Decimal("10"):
            self._warn("La nota debe estar entre 0 y 10")
            self.editGradeValue.setFocus()
            return None
        return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _handle_save_grade(self) -> None:
        if self.selected_row is None:
            self._warn("Debes seleccionar un alumno primero")
            return

        grade_value = self._parse_grade()
        if grade_value is None:
            return

        try:
            with get_session() as session:
                sm_dao = StudentModuleDAOImp(session)
                grade_dao = GradeDAOImp(session)

                enrollment = sm_dao.find_by_id(self.selected_row.enrollment_id)
                if enrollment is None:
                    self._show_error("No se encontró la matrícula del alumno")
                    return

                g = Grade()
                g.student_module = enrollment
                g.grade = grade_value
                g.notes = self.editGradeNotes.text().strip()

                grade_dao.save(g)
                session.commit()

            self._after_grade_change("Nota guardada correctamente")

        except Exception as e:
            self._show_error(f"Error al guardar nota: {e}")

    def _handle_update_grade(self) -> None:
        if self.selected_row is None:
            self._warn("Selecciona un alumno primero")
            return
        if self.editing_grade_id is None:
            self._warn("Selecciona una nota del historial para editar")
            return

        grade_value = self._parse_grade()
        if grade_value is None:
            return

        try:
            with get_session() as session:
                grade_dao = GradeDAOImp(session)
                grade = grade_dao.find_by_id(self.editing_grade_id)
                if grade is None:
                    self._show_error("No se encontró la nota a editar")
                    return

                grade.grade = grade_value
                grade.notes = self.editGradeNotes.text().strip()
                grade_dao.update(grade)
                session.commit()

            self._after_grade_change("Nota actualizada correctamente")

        except Exception as e:
            self._show_error(f"Error al actualizar nota: {e}")

    def _handle_delete_selected_grade(self) -> None:
        if self.selected_row is None:
            self._warn("Selecciona un alumno primero")
            return
        if self.editing_grade_id is None:
            self._warn("Selecciona una nota del historial para eliminar")
            return

        if not self._confirm("Eliminar nota", "¿Seguro que quieres eliminar la nota seleccionada?"):
            return

        try:
            with get_session() as session:
                grade_dao = GradeDAOImp(session)
                grade_dao.delete_by_id(self.editing_grade_id)
                session.commit()

            self._after_grade_change("Nota eliminada")

        except Exception as e:
            self._show_error(f"Error al eliminar nota: {e}")

    def _handle_delete_all_grades(self) -> None:
        if self.selected_row is None:
            self._warn("Selecciona un alumno primero")
            return

        if not self._confirm("Borrar todas", "¿Seguro que quieres borrar TODAS las notas de este alumno en el módulo?"):
            return

        try:
            with get_session() as session:
                grade_dao = GradeDAOImp(session)
                grade_dao.delete_by_student_module(self.selected_row.enrollment_id)
                session.commit()

            self._after_grade_change("Todas las notas borradas")

        except Exception as e:
            self._show_error(f"Error al borrar notas: {e}")

    def _after_grade_change(self, message: str) -> None:
        # refrescar vista
        current_enrollment = self.selected_row.enrollment_id if self.selected_row else None
        self._load_students_for_selected_module()

        # re-seleccionar fila previa si existe
        if current_enrollment is not None:
            for idx, row in enumerate(self.filtered_rows):
                if row.enrollment_id == current_enrollment:
                    self.summaryTable.selectRow(idx)
                    break

        self.editGradeValue.clear()
        self.editGradeNotes.clear()
        self.editing_grade_id = None
        self.btnUpdateGrade.setEnabled(False)
        self.btnDeleteGrade.setEnabled(False)

        QMessageBox.information(self, "OK", message)

    def _handle_logout(self) -> None:
        # Impedir los imports circulares
        from services.login_window import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()

    def _confirm(self, title: str, text: str) -> bool:
        res = QMessageBox.question(self, title, text)
        return res == QMessageBox.StandardButton.Yes

    def _warn(self, msg: str) -> None:
        QMessageBox.warning(self, "Aviso", msg)

    def _show_error(self, msg: str) -> None:
        QMessageBox.critical(self, "Error", msg)