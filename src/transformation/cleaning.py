from __future__ import annotations

from typing import Any
from src.shared.utils import normalize_whitespace, parse_year, union_unique_preserve_order

def clean_string(value: Any) -> str | None:
    return normalize_whitespace(None if value is None else str(value))

def clean_list(values: Any) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        values = [values]
    cleaned = []
    for item in values:
        item_text = clean_string(item)
        if item_text:
            cleaned.append(item_text)
    return union_unique_preserve_order(cleaned)

def clean_year(value: Any) -> int | None:
    return parse_year(value)
