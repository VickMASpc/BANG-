import json
import sqlite3
from pathlib import Path

from gamehub_manager.app import LibraryRefreshService
from gamehub_manager.db.database import Database
from gamehub_manager.db.repositories import GameRepository
from gamehub_manager.drives.detector import DriveDetector
from gamehub_manager.drives.scanner import LibraryScanner
from gamehub_manager.library.indexer import LibraryIndexer
from tests.helpers import create_fake_drive


def test_scanned_games_persist_in_db_and_support_queries(tmp_path: Path) -> None:
    drive_root = tmp_path / "DriveE"
    library_root = create_fake_drive(drive_root)

    ready_game = library_root / "games" / "PC Games" / "Hades"
    ready_game.mkdir(parents=True)
    (ready_game / "Hades.exe").write_text("", encoding="utf-8")
    (ready_game / "game.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "Hades",
                "game_type": "pc",
                "executable_path": "Hades.exe",
            }
        ),
        encoding="utf-8",
    )

    needs_setup_game = library_root / "games" / "PC Games" / "Unknown"
    needs_setup_game.mkdir(parents=True)

    database = Database(tmp_path / "gamehub.db")
    database.initialize()
    repository = GameRepository(database)
    indexer = LibraryIndexer(repository)
    service = LibraryRefreshService(
        DriveDetector(drive_roots_provider=lambda: [drive_root]),
        LibraryScanner(),
        repository,
        indexer,
    )

    snapshot = service.refresh_library_snapshot()

    assert len(snapshot.games) == 2
    assert len(repository.list_all_games()) == 2
    assert len(repository.list_games_by_drive(str(drive_root))) == 2
    assert len(repository.list_needs_setup_games()) == 1
    assert repository.list_installed_games() == []
    assert {game["install_status_label"] for game in snapshot.games} == {"Not installed", "Needs setup"}


def test_installed_game_remains_queryable_when_source_drive_is_absent(tmp_path: Path) -> None:
    drive_root = tmp_path / "DriveE"
    library_root = create_fake_drive(drive_root)
    game_dir = library_root / "games" / "PC Games" / "Dead Cells"
    game_dir.mkdir(parents=True)
    (game_dir / "DeadCells.exe").write_text("", encoding="utf-8")
    (game_dir / "game.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "Dead Cells",
                "game_type": "pc",
                "executable_path": "DeadCells.exe",
            }
        ),
        encoding="utf-8",
    )

    database = Database(tmp_path / "gamehub.db")
    database.initialize()
    repository = GameRepository(database)
    indexer = LibraryIndexer(repository)

    roots = [drive_root]
    service = LibraryRefreshService(
        DriveDetector(drive_roots_provider=lambda: roots),
        LibraryScanner(),
        repository,
        indexer,
    )

    first_snapshot = service.refresh_library_snapshot()
    game = first_snapshot.games[0]
    repository.upsert_installation(game["variant_key"], tmp_path / "Installed" / "Dead Cells", "DeadCells.exe", "installed")

    roots.clear()
    second_snapshot = service.refresh_library_snapshot()

    installed_rows = repository.list_installed_games()
    assert len(installed_rows) == 1
    assert installed_rows[0]["source_drive_root_last_seen"] is None
    assert second_snapshot.games[0]["drive_status_label"] == "Source unavailable"
    assert second_snapshot.games[0]["install_status_label"] == "Installed"


def test_database_initialize_preserves_existing_rows_and_adds_missing_columns(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        CREATE TABLE games (
          id TEXT NOT NULL,
          variant_key TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          game_type TEXT NOT NULL,
          source_type TEXT NOT NULL,
          metadata_status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO games(id, variant_key, title, game_type, source_type, metadata_status, created_at, updated_at)
        VALUES('doom', 'games/pc-games/doom', 'Doom', 'pc', 'drive', 'ready', 'a', 'b')
        """
    )
    connection.commit()
    connection.close()

    database = Database(database_path)
    database.initialize()

    with database.connect() as migrated:
        columns = {
            str(row["name"])
            for row in migrated.execute("PRAGMA table_info(games)").fetchall()
        }
        row = migrated.execute("SELECT title, is_primary FROM games WHERE variant_key = ?", ("games/pc-games/doom",)).fetchone()

    assert "is_primary" in columns
    assert row is not None
    assert row["title"] == "Doom"


def test_duplicate_ids_persist_with_single_primary_variant(tmp_path: Path) -> None:
    drive_root = tmp_path / "DriveE"
    library_root = create_fake_drive(drive_root)

    pc_game_dir = library_root / "games" / "PC Games" / "Doom"
    pc_game_dir.mkdir(parents=True)
    (pc_game_dir / "Doom.exe").write_text("", encoding="utf-8")
    (pc_game_dir / "game.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "Doom",
                "game_type": "pc",
                "executable_path": "Doom.exe",
            }
        ),
        encoding="utf-8",
    )

    emulator_dir = library_root / "games" / "Emulators" / "DOSBox"
    emulator_game_dir = emulator_dir / "Doom"
    emulator_game_dir.mkdir(parents=True)
    (emulator_game_dir / "doom.rom").write_text("", encoding="utf-8")
    (emulator_game_dir / "game.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "Doom",
                "game_type": "emulated",
                "rom_path": "doom.rom",
            }
        ),
        encoding="utf-8",
    )

    database = Database(tmp_path / "gamehub.db")
    database.initialize()
    repository = GameRepository(database)
    service = LibraryRefreshService(
        DriveDetector(drive_roots_provider=lambda: [drive_root]),
        LibraryScanner(),
        repository,
        LibraryIndexer(repository),
    )

    snapshot = service.refresh_library_snapshot()
    doom_rows = [row for row in snapshot.games if row["id"] == "doom"]

    assert len(doom_rows) == 2
    assert len({row["variant_key"] for row in doom_rows}) == 2
    assert sum(1 for row in doom_rows if row["is_primary"]) == 1
