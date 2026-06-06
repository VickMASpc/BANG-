from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parent
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        "GameHubDriveManager",
        "--noconsole",
        "--clean",
        str(project_root / "gamehub_manager" / "__main__.py"),
    ]
    completed = subprocess.run(command, cwd=str(project_root), check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
