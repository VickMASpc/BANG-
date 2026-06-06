from __future__ import annotations

from pathlib import Path


def _collect_files(root: Path) -> list[Path]:
    return [path for path in root.rglob("*") if path.is_file()]


class InstallVerifier:
    def verify(self, source_path: Path, destination_path: Path) -> tuple[bool, int, int, int, int]:
        source_files = _collect_files(source_path)
        destination_files = _collect_files(destination_path)
        source_count = len(source_files)
        destination_count = len(destination_files)
        source_total = sum(path.stat().st_size for path in source_files)
        destination_total = sum(path.stat().st_size for path in destination_files)
        return (
            source_count == destination_count and source_total == destination_total,
            source_count,
            source_total,
            destination_count,
            destination_total,
        )
