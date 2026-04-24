import sys
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow
from sqlalchemy import text

import db.database

BASE_DIR = Path(__file__).resolve().parent.parent
UI_PATH = BASE_DIR / "ui" / "login.ui"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(UI_PATH, self)


def test_db_connection() -> None:
    try:
        with db.database.get_session() as session:
            session.execute(text("SELECT 1"))
        print("Conexión a BD OK")
    except Exception as e:
        print(f"Error de conexión a BD: {e}")


if __name__ == "__main__":
    # test_db_connection()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())