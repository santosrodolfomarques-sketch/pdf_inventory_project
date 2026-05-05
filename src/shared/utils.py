from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

def ensure_dirs(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def normalize_whitespace(value: str | None) -> str | None:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", str(value)).strip()
    return value or None

def remove_accents_lower(value: str | None) -> str:
    if not value:
        return ""
    import unicodedata
    normalized = unicodedata.normalize("NFKD", str(value))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower().strip()

def safe_slug(value: str, max_len: int = 80) -> str:
    value = remove_accents_lower(value)
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return value[:max_len] or "item"

def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()

def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)

def append_rows_to_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerows(rows)

def union_unique_preserve_order(values: Iterable[Any]) -> list[Any]:
    seen = set()
    output = []
    for value in values:
        marker = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        if marker in seen:
            continue
        seen.add(marker)
        output.append(value)
    return output

def coalesce(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, list) and not value:
            continue
        return value
    return None

def parse_year(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value)
    match = re.search(r"(19|20)\d{2}", text)
    if not match:
        return None
    year = int(match.group(0))
    if 1900 <= year <= 2100:
        return year
    return None

def to_json_string(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else ("" if value is None else str(value))
