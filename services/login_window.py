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

        self.next_window: Optional[QWidget] = None  # evita warning

        self.comboRole.addItems([UserType.PROFESOR.value, UserType.ESTUDIANTE.value])

        self.btnLogin.clicked.connect(self.handle_login)
        self.btnClear.clicked.connect(self.handle_clear)
        self.btnExit.clicked.connect(self.close)
        self.editPassword.returnPressed.connect(self.handle_login)

    def handle_login(self):
        username = self.editUsername.text().strip()
        password = self.editPassword.text().strip()
        role = self.comboRole.currentText()

        if not username:
            QMessageBox.warning(self, "Error", "El campo usuario no puede estar vacío")
            return
        if not password:
            QMessageBox.warning(self, "Error", "El campo contraseña no puede estar vacío")
            return

        try:
            with get_session() as session:
                user_dao = UserDAOImp(session)
                user = user_dao.validate_login(username, password)

                if user is None:
                    QMessageBox.warning(self, "Error", "Usuario o contraseña incorrectos")
                    return

                if user.user_type is None or user.user_type.value != role:
                    QMessageBox.critical(self, "Error", "El rol seleccionado no coincide con tu usuario")
                    return

                if user.user_type == UserType.PROFESOR:
                    self.next_window = TeacherWindow(user_id=user.id)
                else:
                    self.next_window = StudentWindow(user_id=user.id)

            if self.next_window is not None:
                self.next_window.show()
                self.close()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al iniciar sesión: {e}")

    def handle_clear(self):
        self.editUsername.clear()
        self.editPassword.clear()
        self.comboRole.setCurrentIndex(0)
        self.editUsername.setFocus()