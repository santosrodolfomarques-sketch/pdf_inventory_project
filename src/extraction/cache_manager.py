from __future__ import annotations

from pathlib import Path
from typing import Any
from src.shared.utils import read_json, safe_slug, write_json

def build_cache_key(file_stem: str, file_hash: str) -> str:
    return f"{safe_slug(file_stem)}__{file_hash[:12]}"

def build_cache_path(cache_dir: Path, file_stem: str, file_hash: str) -> Path:
    return cache_dir / f"{build_cache_key(file_stem, file_hash)}.json"

def load_cached_extraction(cache_path: Path) -> dict[str, Any] | None:
    if not cache_path.exists():
        return None
    return read_json(cache_path)

def save_cached_extraction(cache_path: Path, data: dict[str, Any]) -> None:
    write_json(cache_path, data)
