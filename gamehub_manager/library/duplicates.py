from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping


def find_duplicate_ids(games: Iterable[Mapping[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for game in games:
        game_id = str(game.get("id") or "").strip()
        if not game_id:
            continue
        grouped[game_id].append(dict(game))
    return {game_id: items for game_id, items in grouped.items() if len(items) > 1}


def compute_primary_variant_keys(games: Iterable[Mapping[str, object]]) -> set[str]:
    grouped = find_games_by_id(games)
    primary_keys: set[str] = set()
    for items in grouped.values():
        if not items:
            continue
        primary_keys.add(str(sorted(items, key=_primary_sort_key)[0].get("variant_key") or ""))
    return {key for key in primary_keys if key}


def annotate_duplicate_state(games: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    rows = [dict(game) for game in games]
    grouped = find_games_by_id(rows)
    primary_keys = compute_primary_variant_keys(rows)

    annotated: list[dict[str, object]] = []
    for row in rows:
        game_id = str(row.get("id") or "").strip()
        duplicates = grouped.get(game_id, [])
        row["duplicate_count"] = len(duplicates)
        row["is_duplicate"] = len(duplicates) > 1
        row["is_primary"] = str(row.get("variant_key") or "") in primary_keys
        annotated.append(row)
    return annotated


def find_games_by_id(games: Iterable[Mapping[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for game in games:
        game_id = str(game.get("id") or "").strip()
        if not game_id:
            continue
        grouped[game_id].append(dict(game))
    return grouped


def _primary_sort_key(game: Mapping[str, object]) -> tuple[int, int, int, str, str]:
    installed_rank = 0 if game.get("local_path") else 1
    source_rank = 0 if game.get("source_drive_root_last_seen") else 1
    metadata_rank = 0 if game.get("metadata_status") == "ready" else 1
    source_relative = str(game.get("source_relative_path") or "")
    variant_key = str(game.get("variant_key") or "")
    return (installed_rank, source_rank, metadata_rank, source_relative.lower(), variant_key.lower())
