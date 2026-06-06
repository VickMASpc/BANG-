from pathlib import Path

from gamehub_manager.db.database import Database


def test_database_initialize_is_idempotent(tmp_path: Path) -> None:
    database = Database(tmp_path / "gamehub.db")

    database.initialize()
    database.initialize()

    with database.connect() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
    assert {"settings", "games", "installations", "install_jobs", "launch_sessions", "playtime"} <= tables
