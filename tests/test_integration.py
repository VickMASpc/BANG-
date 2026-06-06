import json
from pathlib import Path

from gamehub_manager.app import LibraryRefreshService
from gamehub_manager.core.paths import AppPaths
from gamehub_manager.db.database import Database
from gamehub_manager.db.repositories import GameRepository
from gamehub_manager.drives.detector import DriveDetector
from gamehub_manager.drives.scanner import LibraryScanner


def test_first_run_bootstrap_creates_config_and_db(tmp_path: Path) -> None:
    paths = AppPaths.from_env(appdata_root=str(tmp_path / "AppData"))

    paths.ensure_bootstrap()
    Database(paths.database_file).initialize()

    assert paths.config_file.exists()
    assert paths.database_file.exists()


def test_refresh_persists_games_and_marks_sources_disconnected(fake_drive: Path, tmp_path: Path) -> None:
    game_dir = fake_drive / "games" / "PC Games" / "Hyper Light Drifter"
    game_dir.mkdir(parents=True)
    (game_dir / "HyperLightDrifter.exe").write_text("", encoding="utf-8")
    (game_dir / "game.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "Hyper Light Drifter",
                "game_type": "pc",
                "executable_path": "HyperLightDrifter.exe",
            }
        ),
        encoding="utf-8",
    )

    database = Database(tmp_path / "gamehub.db")
    database.initialize()
    repository = GameRepository(database)

    roots = [fake_drive.parent]
    detector = DriveDetector(drive_roots_provider=lambda: roots)
    service = LibraryRefreshService(detector, LibraryScanner(), repository)

    first_snapshot = service.refresh_library_snapshot()
    assert len(first_snapshot.games) == 1
    assert first_snapshot.games[0]["source_drive_root_last_seen"] is not None

    roots.clear()
    second_snapshot = service.refresh_library_snapshot()

    assert len(second_snapshot.games) == 1
    assert second_snapshot.games[0]["source_drive_root_last_seen"] is None
