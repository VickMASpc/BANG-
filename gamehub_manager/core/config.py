from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gamehub_manager.core.constants import APP_NAME


@dataclass(slots=True)
class AppConfig:
    schema_version: int = 1
    app_name: str = APP_NAME
    install_root: str | None = None
    developer_mode: bool = False

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "AppConfig":
        return cls(
            schema_version=int(data.get("schema_version") or 1),
            app_name=str(data.get("app_name") or APP_NAME),
            install_root=_coerce_optional_str(data.get("install_root")),
            developer_mode=bool(data.get("developer_mode") or False),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "app_name": self.app_name,
            "install_root": self.install_root,
            "developer_mode": self.developer_mode,
        }


class ConfigStore:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> AppConfig:
        if not self._path.exists():
            return AppConfig()
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return AppConfig()
        if not isinstance(data, dict):
            return AppConfig()
        return AppConfig.from_mapping(data)

    def save(self, config: AppConfig) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(config.to_mapping(), indent=2), encoding="utf-8")

    def get_install_root(self) -> str | None:
        return self.load().install_root

    def set_install_root(self, path: str) -> None:
        config = self.load()
        config.install_root = path
        self.save(config)


def _coerce_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
