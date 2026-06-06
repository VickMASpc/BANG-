from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget


class InstallPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Install Queue"))
        self.jobs_list = QListWidget()
        self._empty_label = QLabel("No active jobs")
        layout.addWidget(self.jobs_list)
        layout.addWidget(self._empty_label)

    def set_jobs(self, jobs: list[dict]) -> None:
        self.jobs_list.clear()
        if not jobs:
            self._empty_label.setText("No active jobs")
            return
        self._empty_label.setText(f"{len(jobs)} job(s)")
        for job in jobs:
            text = f"{job.get('status', 'unknown')}: {job.get('current_file') or job.get('destination_path')}"
            QListWidgetItem(text, self.jobs_list)
