import sys

from PyQt6.QtWidgets import QApplication
from sqlalchemy import text

import db.database
from services.login_window import LoginWindow


def main():
    app = QApplication(sys.argv)
    w = LoginWindow()
    w.show()
    sys.exit(app.exec())

def test_db_connection() -> None:
    try:
        with db.database.get_session() as session:
            session.execute(text("SELECT 1"))
        print("Conexión a BD OK")
    except Exception as e:
        print(f"Error de conexión a BD: {e}")


if __name__ == "__main__":
    # test_db_connection()
    main()