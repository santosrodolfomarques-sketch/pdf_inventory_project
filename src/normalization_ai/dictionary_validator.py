from __future__ import annotations

from typing import Any

import pandas as pd

from src.shared.utils import normalize_whitespace, remove_accents_lower

REQUIRED_COLUMNS = [
    "campo",
    "valor_original",
    "valor_original_limpo",
    "valor_normalizado",
    "categoria",
    "confianca",
    "acao_recomendada",
    "justificativa",
    "aplicar_automaticamente",
]

VALID_CONFIDENCE = {"alta", "media", "baixa"}
VALID_ACTIONS = {"aplicar automático", "revisar manualmente", "manter original"}


def normalize_confidence(value: Any) -> str:
    text = remove_accents_lower(str(value or ""))
    if text in {"alta", "high"}:
        return "alta"
    if text in {"media", "média", "medium"}:
        return "media"
    if text in {"baixa", "low"}:
        return "baixa"
    return "baixa"


def normalize_action(value: Any) -> str:
    text = remove_accents_lower(str(value or ""))
    if "automatic" in text or "aplicar" in text:
        return "aplicar automático"
    if "manter" in text or "original" in text:
        return "manter original"
    return "revisar manualmente"


def should_apply(confianca: str, acao: str, min_confidence: str = "alta") -> bool:
    order = {"baixa": 1, "media": 2, "alta": 3}
    return acao in {"aplicar automático", "manter original"} and order.get(confianca, 0) >= order.get(min_confidence, 3)


def validate_dictionary_items(
    *,
    target_name: str,
    items: list[dict[str, Any]],
    min_confidence: str = "alta",
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in items:
        original = normalize_whitespace(item.get("valor_original"))
        if not original:
            continue

        key = remove_accents_lower(original)
        if key in seen:
            continue
        seen.add(key)

        normalized = normalize_whitespace(item.get("valor_normalizado")) or original
        category = normalize_whitespace(item.get("categoria"))
        confidence = normalize_confidence(item.get("confianca"))
        action = normalize_action(item.get("acao_recomendada"))
        justification = normalize_whitespace(item.get("justificativa")) or "Sem justificativa informada."

        rows.append({
            "campo": target_name,
            "valor_original": original,
            "valor_original_limpo": key,
            "valor_normalizado": normalized,
            "categoria": category,
            "confianca": confidence,
            "acao_recomendada": action,
            "justificativa": justification,
            "aplicar_automaticamente": should_apply(confidence, action, min_confidence=min_confidence),
        })

    df = pd.DataFrame(rows)
    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            df[column] = None
    return df[REQUIRED_COLUMNS]
