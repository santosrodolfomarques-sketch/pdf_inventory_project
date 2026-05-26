from __future__ import annotations

import re
import unicodedata
from typing import Any


def clean_string(value: Any) -> str | None:
    """Limpa e padroniza o espaçamento de uma string, removendo quebras de linha brutas."""
    if value is None:
        return None
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text if text else None


def clean_year(value: Any) -> int | None:
    """Extrai e valida um ano de quatro dígitos no formato YYYY."""
    if value is None:
        return None
    if isinstance(value, int):
        if 1900 <= value <= 2100:
            return value
        return None
    text = str(value).strip()
    match = re.search(r"\b(19|20)\d{2}\b", text)
    if not match:
        return None
    year = int(match.group(0))
    if 1900 <= year <= 2100:
        return year
    return None


def clean_list(value: Any) -> list[str]:
    """Valida, deduplica e higieniza itens de uma lista ou representação textual de lista."""
    if value is None:
        return []
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in {"nan", "none", "null", "[]"}:
            return []
        # Tenta quebrar strings simples separadas por vírgula se não for JSON válido
        if text.startswith("[") and text.endswith("]"):
            try:
                import json
                raw_items = json.loads(text)
            except Exception:
                raw_items = [text]
        else:
            raw_items = [item.strip() for item in text.split(",") if item.strip()]
    else:
        raw_items = [value]

    seen = set()
    cleaned = []
    for item in raw_items:
        if item is None:
            continue
        text_clean = clean_string(item)
        if not text_clean or text_clean.lower() in {"nan", "none", "null"}:
            continue
        # Deduplica ignorando capitular e acentuação
        marker = remove_accents(text_clean).lower()
        if marker not in seen:
            seen.add(marker)
            cleaned.append(text_clean)
    return cleaned


def remove_accents(value: str) -> str:
    """Remove marcas de acentuação de um texto para comparação estável."""
    normalized = unicodedata.normalize("NFKD", str(value))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))
