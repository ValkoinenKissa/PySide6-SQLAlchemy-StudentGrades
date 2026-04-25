from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QMessageBox,
    QTableWidget,
    QListView,
    QTableWidgetItem,
    QComboBox,
    QPushButton)
from sqlalchemy.exc import SQLAlchemyError

from dao.grade_dao import GradeDAOImp
from dao.student_dao import StudentDAOImp
from dao.student_module_dao import StudentModuleDAOImp
from dao.user_dao import UserDAOImp
from db.database import get_session

# Evita problemas con las rutas y directorios al calcular la ruta al vuelo
BASE_DIR = Path(__file__).resolve().parent.parent
UI_PATH = BASE_DIR / "ui" / "student-view.ui"
# Constante con el aprobado general
PASS_GRADE = Decimal(5.0)

# Dataclass necesaria para la tabla
@dataclass
class ModuleSummaryRow:
    enrollment_id: int
    module_id: int
    module_name: str
    last_grade: str
    avg_grade: str
    status: str

class StudentWindow(QWidget):
    # Quitar los warnings, ya que las referencias a las clases solo se calculan en tiempo de ejecución
    if TYPE_CHECKING:
        lblStudentName: QLabel
        lblGlobalAverage: QLabel
        comboModule: QComboBox
        btnLogout: QPushButton
        modulesSummaryTable: QTableWidget
        gradesHistoryList: QListView

    def __init__(self, user_id: int):
        super().__init__()
        uic.loadUi(UI_PATH, self)
        # Tamaño de ventana fijo
        self.setFixedSize(self.size())


        self.user_id: int = user_id
        # Id real del usuario, en optional por ni es nulo
        self.current_student_id: Optional[int] = None
        # Todas las filas del resumen
        self.master_rows: list[ModuleSummaryRow] = []
        #Tablas con filtro
        self.filtered_rows: list[ModuleSummaryRow] = []
        #Evitar eventos durante la carga
        self._loading = False

        """
        Crea modelo para historial (QStandardItemModel) y lo asigna a gradesHistoryList.
        Llama setup:
        _setup_table()
        _setup_signals()
        _init_data() (cargar datos reales)
        """
        self._grades_model = QStandardItemModel(self)
        self.gradesHistoryList.setModel(self._grades_model)

        self._setup_table()
        self._setup_signals()
        self._init_data()

    # Función para configurar la tabla
    def _setup_table(self):
        table = self.modulesSummaryTable
        # Columnas que tendrá la tabla
        table.setColumnCount(4)
        #Titulos
        table.setHorizontalHeaderLabels(["Módulo", "Última", "Media", "Estado"])
        # selección por filas.
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        #Selección unica
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        # No editable
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    # Este metodo conecta eventos de la UI
    def _setup_signals(self):
        # El boton logout mata la app
        self.btnLogout.clicked.connect(self._handle_logout)
        # Detectar selección del combobox
        self.comboModule.currentIndexChanged.connect(self._on_filter_changed)
        #Cambio en la selección de la tabla
        self.modulesSummaryTable.itemSelectionChanged.connect(self._on_table_selection_changed)

    # Inicialización de los datos, similar a initialize() en javaFX
    def _init_data(self):
        try:
            #Abre sesión con la BD
            with get_session() as session:
                student_dao = StudentDAOImp(session)
                user_dao = UserDAOImp(session)

                # Busca student asociado (find_by_user_id) el id se lo hemos pasado desde login_window
                user = user_dao.find_by_id(self.user_id)
                if user is None:
                    self._show_error("Usuario no encontrado")
                    return

                student = student_dao.find_by_user_id(self.user_id)
                if student is None:
                    self._show_error("No se encontraron datos de estudiante")
                    return
                # Si el id del usuario existe lo asociamos a current_student_id
                self.current_student_id = student.id
                # Mostramos todos los datos del usuario en el label
                self.lblStudentName.setText(
                    f"Alumno/a: {user.first_name} {user.last_name} ({student.course} - {student.grade_group})"
                )

                #Llamamos al metodo para cargar todos los modulos del usuario
            self._load_student_modules()
            # Y el metodo para calcular la nota media en función de todas las materias que el alumno tenga registradas
            self._calculate_overall_average()

        except Exception as e:
            self._show_error(f"Error inicializando ventana de estudiante: {e}")

    def _load_student_modules(self):
        if self.current_student_id is None:
            return

        try:
            with get_session() as session:
                student_module_dao = StudentModuleDAOImp(session)
                grade_dao = GradeDAOImp(session)

                # Consulta las asignaturas que tiene matriculadas el alumno (find_by_student).
                enrollments = student_module_dao.find_by_student(self.current_student_id)
                # Limpia el resumen
                self.master_rows.clear()

                # combo de módulos sin duplicados
                modules_combo: list[tuple[int, str]] = []
                seen: set[int] = set()

                # Por cada alumno se obtiene el módulo en el que esta matriculado
                for enrollment in enrollments:
                    module = enrollment.module

                    # todo
                    if module.id not in seen:
                        seen.add(module.id)
                        modules_combo.append((module.id, module.module_name or "-"))

                    # Obtiene la ultima nota de un modulo
                    latest = grade_dao.find_latest_grade(enrollment.id)
                    #Calcula la media de todas las asignaturas
                    average = grade_dao.calculate_average_grade(enrollment.id) or Decimal("0")

                    # Se muestra un - si el valor es nullo si no se muestra la última nota formateada con dos decimales
                    last_grade = "-" if latest is None else f"{latest.grade:.2f}"
                    # Se muestra un - si el valor de la media es nullo si no se muestra la media formateada con dos decimales
                    avg_grade = "-" if average == Decimal("0") else f"{average:.2f}"

                    # calcula status (Sin notas/Aprobado/Suspenso)
                    if latest is None:
                        status = "Sin notas"
                    elif average >= PASS_GRADE:
                        status = "Aprobado"
                    else:
                        status = "Suspenso"

                        # agrega ModuleSummaryRow a master_rows.
                    self.master_rows.append(
                        ModuleSummaryRow(
                            enrollment_id=enrollment.id,
                            module_id=module.id,
                            module_name=module.module_name or "-",
                            last_grade=last_grade,
                            avg_grade=avg_grade,
                            status=status,
                        )
                    )
            # Carga comboModule
            self._loading = True
            self.comboModule.clear()
            # primer item: "Todos" con data None
            self.comboModule.addItem("Todos", None)

            # Se añade de forma dinamica contenidos al combo
            for module_id, module_name in modules_combo:
                self.comboModule.addItem(module_name, module_id)
            self._loading = False

            #Aplica filtro inicial: _apply_filter(None).
            self._apply_filter(None)

        except Exception as e:
            self._show_error(f"Error al cargar módulos: {e}")

    def _on_filter_changed(self):
        # Si _loading está activo, ignora.
        if self._loading:
            return
        #Lee module_id seleccionado con currentData().
        selected_module_id = self.comboModule.currentData()
        #Llama _apply_filter(...).
        self._apply_filter(selected_module_id)

    def _apply_filter(self, selected_module_id: Optional[int]):
        # Si None: muestra todas las filas.
        if selected_module_id is None:
            self.filtered_rows = list(self.master_rows)
        else:
            #Si id: filtra master_rows por module_id
            self.filtered_rows = [r for r in self.master_rows if r.module_id == selected_module_id]

            # Se llama al renderizado de la tabla pasandole los datos a mostrar
        self._render_table(self.filtered_rows)

        # Si hay filas selecciona la primera
        if self.filtered_rows:
            self.modulesSummaryTable.selectRow(0)
            # carga historial de esa matrícula
            self._load_grades_for_module(self.filtered_rows[0].enrollment_id)
        else:
            # limpia lista historial y muestra mensaje
            self._grades_model.clear()
            self._grades_model.appendRow(QStandardItem("No hay módulos para mostrar"))

    def _render_table(self, rows: list[ModuleSummaryRow]):
        # Se tipa la variable tabla con modulesSummaryTable (y sus ajustes definidos mas arriba)
        table = self.modulesSummaryTable
        # Ajusta el numero de filas
        table.setRowCount(len(rows))

        # Por cada fila setItem columna 0..3 (módulo, última, media, estado).
        for i, row in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(row.module_name))
            table.setItem(i, 1, QTableWidgetItem(row.last_grade))
            table.setItem(i, 2, QTableWidgetItem(row.avg_grade))
            status_item = QTableWidgetItem(row.status)
            # centra texto de estado.
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(i, 3, status_item)

            # resizeColumnsToContents() para autoajuste.
        table.resizeColumnsToContents()

        # Obtiene índice de fila seleccionada en ejecución
    def _on_table_selection_changed(self):
        row_idx = self.modulesSummaryTable.currentRow()
        # valida el rango
        if row_idx < 0 or row_idx >= len(self.filtered_rows):
            return
        # Busca fila en filtered_rows
        selected = self.filtered_rows[row_idx]
        # Carga historial de notas de esa matrícula.
        self._load_grades_for_module(selected.enrollment_id)


    def _load_grades_for_module(self, enrollment_id: int):
        try:
            with get_session() as session:
                grade_dao = GradeDAOImp(session)
                # Consulta notas por matrícula.
                grades = grade_dao.find_by_student_module(enrollment_id)

                # Limpia el historial
            self._grades_model.clear()

            # Si no hay notas: agrega “No hay notas registradas”.
            if not grades:
                self._grades_model.appendRow(QStandardItem("No hay notas registradas"))
                return

            # Si hay nitas se agrega cada nota como string "nota - observaciones"
            for grade in grades:
                text = f"{grade.grade:.2f}"
                if grade.notes:
                    text += f" - {grade.notes}"
                self._grades_model.appendRow(QStandardItem(text))

        except Exception as e:
            self._show_error(f"Error al cargar notas: {e}")


    def _calculate_overall_average(self):
        # Si no se localiza el id del estudiante la etiqueta pondra un -
        if self.current_student_id is None:
            self.lblGlobalAverage.setText("Media general: -")
            return

        try:
            # Si el alumno existe, se llama al metodo del dao que calcula la media de todas las notas de un estudiante
            with get_session() as session:
                grade_dao = GradeDAOImp(session)
                overall = grade_dao.calculate_overall_average_by_student(self.current_student_id)

            if overall == Decimal("0"):
                # Si la media es un 0 no se imprime nada
                self.lblGlobalAverage.setText("Media general: -")
            else:
                #Sino se imprime la media formateada con 2 decimales
                self.lblGlobalAverage.setText(f"Media general: {overall:.2f}")

        except SQLAlchemyError:
            #Si hay algún problema no se muestra nada
            self.lblGlobalAverage.setText("Media general: -")

    def _handle_logout(self):
        from services.login_window import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()

        # Metodo para evitar llamar todo el rato a _showerror
    def _show_error(self, message: str):
        QMessageBox.critical(self, "Error", message)
