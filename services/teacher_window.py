from pathlib import Path

from PyQt6 import uic
from PyQt6.QtWidgets import QWidget

BASE_DIR = Path(__file__).resolve().parent.parent
UI_PATH = BASE_DIR / "ui" / "teacher-view.ui"

class TeacherWindow(QWidget):
    def __init__(self, user_id: int):
        super().__init__()
        uic.loadUi(UI_PATH, self)