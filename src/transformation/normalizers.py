from __future__ import annotations

from typing import Any
from src.shared.config import Settings
from src.shared.utils import remove_accents_lower

def normalize_with_map(value: str | None, mapping: dict[str, str]) -> str | None:
    if not value:
        return None
    key = remove_accents_lower(value)
    if key in mapping:
        return mapping[key]

    for raw_key, mapped_value in mapping.items():
        if raw_key in key:
            return mapped_value

    return value.strip()

def normalize_document_type(value: str | None, settings: Settings) -> str | None:
    return normalize_with_map(value, settings.document_type_map)

def normalize_territorial_scope(value: str | None, settings: Settings) -> str | None:
    return normalize_with_map(value, settings.territorial_scope_map)

def normalize_sector(value: str | None, settings: Settings) -> str | None:
    return normalize_with_map(value, settings.sector_map)

def normalize_method_family(value: str | None, settings: Settings) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    for option in settings.taxonomia_metodos:
        if remove_accents_lower(option) == remove_accents_lower(normalized):
            return option
    for option in settings.taxonomia_metodos:
        if remove_accents_lower(option) in remove_accents_lower(normalized):
            return option
    return "Outros"
