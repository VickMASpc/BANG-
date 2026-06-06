from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class InstallPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Install Queue"))
        layout.addWidget(QLabel("No active jobs"))
