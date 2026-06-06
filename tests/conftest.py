from pathlib import Path

import pytest

from tests.helpers import create_fake_drive


@pytest.fixture()
def fake_drive(tmp_path: Path) -> Path:
    return create_fake_drive(tmp_path / "DriveE")
