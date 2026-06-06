from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from gamehub_manager.core.constants import APP_NAME


@dataclass(slots=True)
class AppPaths:
    root: Path
    logs_dir: Path
    cache_dir: Path
    thumbnails_dir: Path
    config_file: Path
    database_file: Path
    default_install_root: Path

    @classmethod
    def from_env(cls, appdata_root: str | None = None) -> "AppPaths":
        appdata = Path(appdata_root or os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        root = appdata / APP_NAME
        return cls(
            root=root,
            logs_dir=root / "logs",
            cache_dir=root / "cache",
            thumbnails_dir=root / "thumbnails",
            config_file=root / "config.json",
            database_file=root / "gamehub.db",
            default_install_root=Path.home() / "Games" / "GameHub",
        )

    def ensure_bootstrap(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        if not self.config_file.exists():
            self.config_file.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "app_name": APP_NAME,
                        "install_root": None,
                        "developer_mode": False,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        self.database_file.touch(exist_ok=True)
