from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem


class GameTable(QTableWidget):
    game_selected = Signal(dict)

    HEADERS = [
        "Title",
        "Type",
        "Genre",
        "Source",
        "Installed",
        "Install Status",
        "Size",
        "Playtime",
        "Last Played",
        "Drive Status",
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(0, len(self.HEADERS), parent)
        self._games: list[dict[str, Any]] = []
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.itemSelectionChanged.connect(self._emit_selected_game)

    def set_games(self, games: list[dict[str, Any]]) -> None:
        self._games = games
        self.setRowCount(len(games))
        for row_index, game in enumerate(games):
            values = [
                game.get("title", ""),
                game.get("game_type", ""),
                game.get("genre", ""),
                game.get("source_relative_path", ""),
                "Yes" if game.get("local_path") else "No",
                game.get("install_status") or "Not installed",
                self._format_size(game.get("size_bytes")),
                self._format_playtime(game.get("total_seconds")),
                game.get("last_played_at") or "",
                "Connected" if game.get("source_drive_root_last_seen") else "Disconnected",
            ]
            for column_index, value in enumerate(values):
                self.setItem(row_index, column_index, QTableWidgetItem(str(value)))
        if games:
            self.selectRow(0)
        else:
            self.game_selected.emit({})

    def _emit_selected_game(self) -> None:
        rows = self.selectionModel().selectedRows()
        if not rows:
            self.game_selected.emit({})
            return
        self.game_selected.emit(self._games[rows[0].row()])

    @staticmethod
    def _format_size(size_bytes: Any) -> str:
        if not size_bytes:
            return ""
        size = float(size_bytes)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                return f"{size:.1f} {unit}"
            size /= 1024
        return ""

    @staticmethod
    def _format_playtime(total_seconds: Any) -> str:
        if not total_seconds:
            return ""
        hours = int(total_seconds) // 3600
        minutes = (int(total_seconds) % 3600) // 60
        return f"{hours}h {minutes}m"
