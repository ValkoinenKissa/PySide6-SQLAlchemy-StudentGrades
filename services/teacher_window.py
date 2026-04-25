from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PyQt6 import uic

# importación de todos los componentes de Qt necesarios
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
# Función que abre una sesión con la base de datos.
from db.models import Grade
from dao.teacher_dao import TeacherDAOImp
from dao.student_module_dao import StudentModuleDAOImp
from dao.grade_dao import GradeDAOImp
from dao.user_dao import UserDAOImp

# Evita problemas con las rutas y directorios al calcular la ruta al vuelo con Path
BASE_DIR = Path(__file__).resolve().parent.parent
UI_PATH = BASE_DIR / "ui" / "teacher-view.ui"


# Data class necesaria para la tabla de estudiantes
# Guarda la información que se mostrará en pantalla.
@dataclass
class StudentModuleRow:
    enrollment_id: int
    student_name: str
    course: str # Curso del alumno (primero, segundo..)
    group: str # Grupo del alumno (DAM, ASIR)
    last_grade: str
    avg_grade: str
    grade_count: str

# Data class necesaria para la tabla del historial de notas
# Guarda la información que se mostrará en pantalla.
@dataclass
class GradeRow:
    grade_id: int
    grade_value: str
    notes: str


class TeacherWindow(QWidget):
    # Estas anotaciones solo se usan para que el editor / type checker
    # conozca los nombres de los widgets cargados desde el archivo .ui.
    # No se crean realmente aquí; los crea uic.loadUi().

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
        # Cargar el archivo .ui
        # El propio objeto "self" recibe los widgets definidos en ese archivo.
        uic.loadUi(str(UI_PATH), self)
        # Tamaño de ventana fijo
        self.setFixedSize(self.size())


        # ID del usuario autenticado.
        self.user_id = user_id

        # ID real del profesor en la base de datos.
        # Se usa Optional[int] porque al principio puede ser None.
        self.current_teacher_id: Optional[int] = None

        # Fila seleccionada actualmente en la tabla de alumnos.
        self.selected_row: Optional[StudentModuleRow] = None

        # ID de la nota que se está editando actualmente.
        self.editing_grade_id: Optional[int] = None

        # Lista con todos los alumnos del módulo actual.
        # Se conserva para poder filtrar en cache sin volver a consultar la BD cada vez.
        self.master_rows: list[StudentModuleRow] = []

        # Lista filtrada que realmente se está mostrando en la tabla.
        self.filtered_rows: list[StudentModuleRow] = []

        # Variable para evitar que ciertos eventos se disparen
        # mientras la interfaz se está cargando o actualizando.
        self._loading = False

        # Configuración inicial de tablas, señales y datos.
        self._setup_tables()
        self._setup_signals()
        self._init_data()

    # Configuración de las tablas
    def _setup_tables(self) -> None:
        # Número de columnas y nombres que tendrá la tabla resumen.
        self.summaryTable.setColumnCount(6)
        self.summaryTable.setHorizontalHeaderLabels(
            ["Alumno/a", "Curso", "Grupo", "Última", "Media", "Notas"]
        )
        # Títulos visibles de las columnas.
        self.summaryTable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Al seleccionar algo, se selecciona la fila completa.
        self.summaryTable.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        # Impide editar celdas directamente con doble clic o similar.
        self.summaryTable.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Historial notas
        # Número de columnas y nombres que tendrá la tabla historial notas.
        self.gradesHistoryTable.setColumnCount(2)
        self.gradesHistoryTable.setHorizontalHeaderLabels(["Nota", "Observaciones"])

        # Títulos visibles de las columnas.
        self.gradesHistoryTable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Al seleccionar algo, se selecciona la fila completa.
        self.gradesHistoryTable.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        # Impide editar celdas directamente con doble clic o similar.
        self.gradesHistoryTable.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Estos botones deben empezar desactivados porque aún no hay nota seleccionada.
        self.btnUpdateGrade.setEnabled(False)
        self.btnDeleteGrade.setEnabled(False)
        self.btnClearGrade.setEnabled(False)

    # Este método actúa de listener, asigna acciones a los botones
    def _setup_signals(self) -> None:

        # Botón de cerrar sesión.
        self.btnLogout.clicked.connect(self._handle_logout)

        # Botón de recargar datos.
        self.btnRefresh.clicked.connect(self._load_students_for_selected_module)

        # Cuando cambia el módulo seleccionado en el comboBox, se recargan los alumnos.
        self.comboModuleFilter.currentIndexChanged.connect(self._on_module_changed)

        # Al escribir en el buscador, se filtra la lista de alumnos.
        self.editStudentSearch.textChanged.connect(self._filter_students)

        # Cuando cambia la selección en la tabla principal, se carga el historial de notas (gradesHistoryTable).
        self.summaryTable.itemSelectionChanged.connect(self._on_student_selected)

        # Cuando cambia la selección en la tabla de notas, se cargan los datos en el formulario (Nota observaciones).
        self.gradesHistoryTable.itemSelectionChanged.connect(self._on_grade_selected)

        # Botones relacionados con las funciones CRUD de las notas.
        self.btnSaveGrade.clicked.connect(self._handle_save_grade)
        self.btnUpdateGrade.clicked.connect(self._handle_update_grade)
        self.btnDeleteGrade.clicked.connect(self._handle_delete_selected_grade)
        self.btnClearGrade.clicked.connect(self._handle_delete_all_grades)

    # Inicialización de los datos
    def _init_data(self) -> None:
        try:
            with get_session() as session:
                # Creamos los DAO necesarios usando la sesión de base de datos.
                user_dao = UserDAOImp(session)
                teacher_dao = TeacherDAOImp(session)

                # Buscamos el usuario autenticado.
                user = user_dao.find_by_id(self.user_id)
                if user is None:
                    self._show_error("Usuario no encontrado")
                    return


                # Buscamos el profesor asociado a ese usuario.
                teacher = teacher_dao.find_by_user_id(self.user_id)
                if teacher is None:
                    self._show_error("No se encontraron datos de profesor")
                    return

                # Guardamos el ID real del profesor.
                self.current_teacher_id = teacher.id
                # Mostramos el nombre del profesor en la interfaz (label).
                self.lblSelectedStudent.setText(f"Profesor/a: {user.first_name} {user.last_name}")

                # Una vez sabemos qué profesor es, cargamos sus módulos (AD, PMDM..).
            self._load_teacher_modules()

        except Exception as e:
            self._show_error(f"Error al inicializar profesor: {e}")

    # modulos y alumnos
    def _load_teacher_modules(self) -> None:
        # Si no sabemos qué profesor está logueado, no podemos cargar módulos.
        if self.current_teacher_id is None:
            return

        try:
            with get_session() as session:
                teacher_dao = TeacherDAOImp(session)
                modules = teacher_dao.get_modules_by_teacher(self.current_teacher_id)
                # Obtenemos la lista de módulos impartidos por este profesor.

            # Marcamos que estamos actualizando la interfaz para evitar eventos redundantes.
            self._loading = True
            # Limpiamos el combo de módulos.
            self.comboModuleFilter.clear()

            # Añadimos cada módulo al comboBox.
            # El texto visible será module_name.
            # El dato asociado será m.id, que luego recuperamos con currentData().
            for m in modules:
                self.comboModuleFilter.addItem(m.module_name or "-", m.id)
            self._loading = False

            # Si hay módulos, seleccionamos el primero y cargamos sus alumnos.
            if modules:
                self.comboModuleFilter.setCurrentIndex(0)
                self._load_students_for_selected_module()
                # Si no hay módulos, vaciamos la tabla.
            else:
                self.summaryTable.setRowCount(0)

        except Exception as e:
            self._show_error(f"Error al cargar módulos: {e}")

    def _on_module_changed(self) -> None:
        # Si el cambio lo hemos provocado nosotros al cargar datos, no hacemos nada.
        if self._loading:
            return
        # Si el usuario cambia el módulo, recargamos los alumnos.
        self._load_students_for_selected_module()

    def _load_students_for_selected_module(self) -> None:
        # Obtenemos el ID del módulo seleccionado en el combo.
        module_id = self.comboModuleFilter.currentData()

        # Si no hay módulo seleccionado, vaciamos la tabla.
        if module_id is None:
            self.summaryTable.setRowCount(0)
            return

        try:
            with get_session() as session:
                sm_dao = StudentModuleDAOImp(session)
                grade_dao = GradeDAOImp(session)

                # Buscamos todas las matrículas/alumnos del módulo.
                enrollments = sm_dao.find_by_module(module_id)

                # Lista final que se mostrará en la tabla.
                rows: list[StudentModuleRow] = []

                for enrollment in enrollments:
                    # Cada enrollment representa una matrícula alumno-módulo.
                    student = enrollment.student
                    # Nombre completo del alumno.
                    student_name = f"{student.user.first_name} {student.user.last_name}"

                    # Notas del alumno en esa matrícula concreta.
                    grades = grade_dao.find_by_student_module(enrollment.id)
                    # Contamos cuántas notas tiene.
                    grade_count = str(len(grades))
                    # Valores por defecto si todavía no tiene notas.
                    last_grade = "-"
                    avg_grade = "-"

                    if grades:
                        # La consulta devuelve las notas ordenadas de más reciente a más antigua.
                        latest = grades[0]
                        # Se asigna la variable de la tabla
                        last_grade = f"{latest.grade:.2f}"

                        # Calculamos la media solo si hay notas.
                        avg = grade_dao.calculate_average_grade(enrollment.id)
                        if avg is not None:
                            avg_grade = f"{avg:.2f}"

                    # Creamos la fila que luego se mostrará en la tabla
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

            # Guardamos los datos "maestros".
            self.master_rows = rows
            # Pintamos la tabla con los datos obtenidos.
            self._render_students(rows)

            # Reseteamos selección de alumno y elementos del panel de notas.
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
        # Guardamos la lista visible actual.
        self.filtered_rows = rows

        # Ajustamos el número de filas de la tabla.
        self.summaryTable.setRowCount(len(rows))

        # Rellenamos cada celda.
        for i, row in enumerate(rows):
            self.summaryTable.setItem(i, 0, QTableWidgetItem(row.student_name))
            self.summaryTable.setItem(i, 1, QTableWidgetItem(row.course))
            self.summaryTable.setItem(i, 2, QTableWidgetItem(row.group))
            self.summaryTable.setItem(i, 3, QTableWidgetItem(row.last_grade))
            self.summaryTable.setItem(i, 4, QTableWidgetItem(row.avg_grade))
            self.summaryTable.setItem(i, 5, QTableWidgetItem(row.grade_count))

        # Ajusta el ancho de las columnas al contenido.
        self.summaryTable.resizeColumnsToContents()

    def _filter_students(self, text: str) -> None:
        # Normalizamos el texto de búsqueda.
        q = (text or "").strip().lower()

        # Si no hay texto, mostramos todo
        if not q:
            self._render_students(self.master_rows)
            return


        # Filtramos por nombre de alumno.

        """
        List Comprehension
        
        [ ... ]: Los corchetes indican que el resultado final será una lista.
        r: Es el elemento que se agregará a la nueva lista (el "output").
        for r in self.master_rows: Es el bucle que recorre la fuente de datos original.
        if q in r.student_name.lower(): Es la cláusula de filtrado. 
        Solo los elementos que cumplan esta condición pasarán a la lista filtered.
        """
        filtered = [r for r in self.master_rows if q in r.student_name.lower()]
        # Dibujar en la tabla la lista filtrada
        self._render_students(filtered)

    # selección de alumno y carga del historial de notas
    def _on_student_selected(self) -> None:
        # Fila seleccionada en la tabla principal (summary table)
        row_idx = self.summaryTable.currentRow()

        # Validación para evitar índices inválidos.
        if row_idx < 0 or row_idx >= len(self.filtered_rows):
            return

        # Obtenemos la fila de datos correspondiente.
        row = self.filtered_rows[row_idx]
        self.selected_row = row

        # Mostramos el nombre del alumno seleccionado.
        self.lblGradesStudentName.setText(row.student_name)

        # Al seleccionar un alumno, reseteamos edición de nota y deshabilitamos algunos botones
        self.editing_grade_id = None
        self.btnUpdateGrade.setEnabled(False)
        self.btnDeleteGrade.setEnabled(False)

        # Ahora sí permitimos borrar todas las notas de ese alumno.
        self.btnClearGrade.setEnabled(True)

        # Cargamos el historial de notas de ese alumno-módulo.
        self._load_grades_history(row.enrollment_id)

    def _load_grades_history(self, enrollment_id: int) -> None:
        try:
            with get_session() as session:
                grade_dao = GradeDAOImp(session)
                grades = grade_dao.find_by_student_module(enrollment_id)

            # Preparar la tabla con tantas filas como notas haya.
            self.gradesHistoryTable.setRowCount(len(grades))

            for i, g in enumerate(grades):
                # Formateamos la nota con 2 decimales.
                val = f"{g.grade:.2f}"
                # Si no hay observaciones, usamos cadena vacía.
                notes = g.notes or ""

                # Creamos la celda de la nota.
                grade_item = QTableWidgetItem(val)


                # Guardamos el ID real de la nota dentro del item.
                # Así luego podemos recuperar qué nota se ha seleccionado.
                grade_item.setData(0x0100, g.id)
                self.gradesHistoryTable.setItem(i, 0, grade_item)
                self.gradesHistoryTable.setItem(i, 1, QTableWidgetItem(notes))

            # Ajustamos columnas al contenido.
            self.gradesHistoryTable.resizeColumnsToContents()

            # Al recargar historial, no debe haber una nota marcada para editar.
            self.btnDeleteGrade.setEnabled(False)

        except Exception as e:
            self._show_error(f"Error cargando historial: {e}")

    def _on_grade_selected(self) -> None:
        # Fila seleccionada en el historial de notas.
        row_idx = self.gradesHistoryTable.currentRow()

        # Si no hay fila válida, desactivamos edición.
        if row_idx < 0:
            self.editing_grade_id = None
            self.btnUpdateGrade.setEnabled(False)
            self.btnDeleteGrade.setEnabled(False)
            return

        # Obtenemos la celda de la nota y observaciones.
        item_grade = self.gradesHistoryTable.item(row_idx, 0)
        item_notes = self.gradesHistoryTable.item(row_idx, 1)


        if item_grade is None:
            return

        # Recuperamos el ID oculto que habíamos guardado en el item.
        grade_id = item_grade.data(0x0100)
        self.editing_grade_id = int(grade_id) if grade_id is not None else None

        # Cargamos el valor de la nota en el campo de edición.
        self.editGradeValue.setText(item_grade.text().replace(",", "."))

        # Cargamos las observaciones en el campo de texto.
        self.editGradeNotes.setText(item_notes.text() if item_notes else "")

        # Activamos botones si realmente hay una nota seleccionada.
        self.btnUpdateGrade.setEnabled(self.editing_grade_id is not None)
        self.btnDeleteGrade.setEnabled(self.editing_grade_id is not None)

    # crud de notas
    def _parse_grade(self) -> Optional[Decimal]:
        # Cogemos el texto del campo de nota.
        raw = self.editGradeValue.text().strip().replace(",", ".")

        # Si el campo está vacío, avisamos.
        if not raw:
            self._warn("Debes introducir una nota")
            self.editGradeValue.setFocus()
            return None
        try:
            # Convertimos a Decimal para evitar errores de precisión.
            val = Decimal(raw)
        except InvalidOperation:
            self._warn("La nota debe ser un número válido")
            self.editGradeValue.setFocus()
            return None

        # Validación de rango de la nota.
        if val < Decimal("0") or val > Decimal("10"):
            self._warn("La nota debe estar entre 0 y 10")
            self.editGradeValue.setFocus()
            return None

        # Redondeamos a 2 decimales
        return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _handle_save_grade(self) -> None:
        # No se puede guardar una nota si no hay alumno seleccionado.
        if self.selected_row is None:
            self._warn("Debes seleccionar un alumno primero")
            return

        # Validamos la nota introducida.
        grade_value = self._parse_grade()
        if grade_value is None:
            return

        try:
            with get_session() as session:
                sm_dao = StudentModuleDAOImp(session)
                grade_dao = GradeDAOImp(session)

                # Buscamos la matrícula exacta del alumno.
                enrollment = sm_dao.find_by_id(self.selected_row.enrollment_id)
                if enrollment is None:
                    self._show_error("No se encontró la matrícula del alumno")
                    return

                 # Creamos una nueva nota (de la dataclass)
                g = Grade()
                g.student_module = enrollment
                g.grade = grade_value
                g.notes = self.editGradeNotes.text().strip()


                # Guardamos la nota.
                grade_dao.save(g)
                session.commit()

            # Tras guardar, refrescamos la vista.
            self._after_grade_change("Nota guardada correctamente")

        except Exception as e:
            self._show_error(f"Error al guardar nota: {e}")

    def _handle_update_grade(self) -> None:
        # Validaciones previas.
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

                # Buscamos la nota por ID.
                grade = grade_dao.find_by_id(self.editing_grade_id)
                if grade is None:
                    self._show_error("No se encontró la nota a editar")
                    return

                # Actualizamos campos.
                grade.grade = grade_value
                grade.notes = self.editGradeNotes.text().strip()

                # Persistimos los cambios
                grade_dao.update(grade)
                session.commit()

            self._after_grade_change("Nota actualizada correctamente")

        except Exception as e:
            self._show_error(f"Error al actualizar nota: {e}")

    def _handle_delete_selected_grade(self) -> None:

        # Validaciones.
        if self.selected_row is None:
            self._warn("Selecciona un alumno primero")
            return
        if self.editing_grade_id is None:
            self._warn("Selecciona una nota del historial para eliminar")
            return

        # Pedimos confirmación al usuario antes de borrar.
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

        # Confirmación fuerte, porque esto elimina todo el historial del alumno en ese módulo.
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
        # Guardamos la matrícula seleccionada antes de recargar.
        # Así intentamos volver a seleccionar esa misma fila después.
        current_enrollment = self.selected_row.enrollment_id if self.selected_row else None
        self._load_students_for_selected_module()

        # re-seleccionar fila previa si existe
        if current_enrollment is not None:
            for idx, row in enumerate(self.filtered_rows):
                if row.enrollment_id == current_enrollment:
                    self.summaryTable.selectRow(idx)
                    break

        # Limpiamos el formulario de edición.
        self.editGradeValue.clear()
        self.editGradeNotes.clear()
        self.editing_grade_id = None
        self.btnUpdateGrade.setEnabled(False)
        self.btnDeleteGrade.setEnabled(False)

        # Mostramos mensaje informativo final.
        QMessageBox.information(self, "OK", message)

    def _handle_logout(self) -> None:
        # Impedir los imports circulares
        from services.login_window import LoginWindow

        # Creamos una nueva ventana de login.
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()

    def _confirm(self, title: str, text: str) -> bool:
        # Muestra un cuadro de confirmación y devuelve True si el usuario acepta.
        res = QMessageBox.question(self, title, text)
        return res == QMessageBox.StandardButton.Yes

    def _warn(self, msg: str) -> None:
        # Mensaje de advertencia.
        QMessageBox.warning(self, "Aviso", msg)

    def _show_error(self, msg: str) -> None:
        # Mensaje crítico
        QMessageBox.critical(self, "Error", msg)