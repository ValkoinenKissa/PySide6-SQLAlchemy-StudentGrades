from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QComboBox, QLineEdit, QPushButton, QMessageBox

from dao import UserDAOImp
from db.database import get_session
from db.models import UserType
from services.student_window import StudentWindow
from services.teacher_window import TeacherWindow

BASE_DIR = Path(__file__).resolve().parent.parent
UI_PATH = BASE_DIR / "ui" / "login.ui"


class LoginWindow(QWidget):
    # Quitar los warnings, ya que las referencias a las clases solo se calculan en tiempo de ejecución
    if TYPE_CHECKING:
        comboRole: QComboBox
        editUsername: QLineEdit
        editPassword: QLineEdit
        btnLogin: QPushButton
        btnClear: QPushButton
        btnExit: QPushButton

    def __init__(self):
        super().__init__()
        uic.loadUi(str(UI_PATH), self)
        self.setFixedSize(self.size())
        self.setWindowTitle("Login")

        self.next_window: Optional[QWidget] = None


        # Configuramos las acciones de los botones

        self.comboRole.addItems([UserType.PROFESOR.value, UserType.ESTUDIANTE.value])
        self.btnLogin.clicked.connect(self.handle_login)
        self.btnClear.clicked.connect(self.handle_clear)
        self.btnExit.clicked.connect(self.close)
        self.editPassword.returnPressed.connect(self.handle_login)

    # Función para gestionar el login
    def handle_login(self):
        username = self.editUsername.text().strip()
        password = self.editPassword.text().strip()
        role = self.comboRole.currentText()

        # Verificación campos usuario y pass
        if not username:
            QMessageBox.warning(self, "Error", "El campo usuario no puede estar vacío")
            return
        if not password:
            QMessageBox.warning(self, "Error", "El campo contraseña no puede estar vacío")
            return

        # Se opbtiene conexion con el conector de la bd y se le pasa la conexion al DAO de usuarios
        try:
            with get_session() as session:
                user_dao = UserDAOImp(session)
                #Se ejecuta la validación del usuario
                user = user_dao.validate_login(username, password)

                if user is None:
                    # Si es nulo se muestra el mensaje de alerta
                    QMessageBox.warning(self, "Error", "Usuario o contraseña incorrectos")
                    return

                #Si el usuario es correcto, pero el rol seleccionado no es el rol correcto
                if user.user_type is None or user.user_type.value != role:
                    QMessageBox.critical(self, "Error", "El rol seleccionado no coincide con tu usuario")
                    return

                #Si el usuario tiene el rol profesor, se carga la ventana del profesor, sino la del alumno
                if user.user_type == UserType.PROFESOR:
                    self.next_window = TeacherWindow(user_id=user.id)
                else:
                    self.next_window = StudentWindow(user_id=user.id)

            # Se muestra la siguiente ventana seleccionada y se oculta la actual
            if self.next_window is not None:
                self.next_window.show()
                self.close()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al iniciar sesión: {e}")

    # funcion para limpiar los campos y el combobox
    def handle_clear(self):
        self.editUsername.clear()
        self.editPassword.clear()
        self.comboRole.setCurrentIndex(0)
        self.editUsername.setFocus()