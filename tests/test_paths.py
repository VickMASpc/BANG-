from pathlib import Path

from gamehub_manager.core.paths import AppPaths


def test_app_paths_bootstrap_creates_expected_files(tmp_path: Path) -> None:
    paths = AppPaths.from_env(appdata_root=str(tmp_path / "AppData"))

    paths.ensure_bootstrap()

    assert paths.root.exists()
    assert paths.logs_dir.exists()
    assert paths.cache_dir.exists()
    assert paths.thumbnails_dir.exists()
    assert paths.config_file.exists()
    assert paths.database_file.exists()
