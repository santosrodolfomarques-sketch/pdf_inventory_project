from __future__ import annotations

from typing import Any
from .utils import coalesce, normalize_whitespace, parse_year, union_unique_preserve_order

EXTRACTION_FIELDS = [
    "nome_documento",
    "tipo_documento",
    "ano_publicacao",
    "horizonte_temporal",
    "abrangencia_territorial",
    "setor",
    "temas",
    "aplicou_estudo_futuro",
    "tipo_estudo_futuro",
    "metodos_estudo_futuro",
    "familia_do_metodo",
    "referencias",
    "condicionantes_estudo_futuro",
    "instituicoes_apoio",
    "instituicao_responsavel",
]

LIST_FIELDS = [
    "temas",
    "metodos_estudo_futuro",
    "referencias",
    "condicionantes_estudo_futuro",
    "instituicoes_apoio",
]

STRING_FIELDS = [
    "nome_documento",
    "tipo_documento",
    "abrangencia_territorial",
    "setor",
    "tipo_estudo_futuro",
    "familia_do_metodo",
    "instituicao_responsavel",
]

def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = [value]
    cleaned = []
    for item in items:
        if item is None:
            continue
        item_text = normalize_whitespace(str(item))
        if item_text:
            cleaned.append(item_text)
    return union_unique_preserve_order(cleaned)

def _coerce_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    true_values = {"true", "sim", "yes", "1"}
    false_values = {"false", "nao", "não", "no", "0"}
    if text in true_values:
        return True
    if text in false_values:
        return False
    return None

def empty_payload() -> dict[str, Any]:
    return {
        "nome_documento": None,
        "tipo_documento": None,
        "ano_publicacao": None,
        "horizonte_temporal": None,
        "abrangencia_territorial": None,
        "setor": None,
        "temas": [],
        "aplicou_estudo_futuro": None,
        "tipo_estudo_futuro": None,
        "metodos_estudo_futuro": [],
        "familia_do_metodo": None,
        "referencias": [],
        "condicionantes_estudo_futuro": [],
        "instituicoes_apoio": [],
        "instituicao_responsavel": None,
    }

def normalize_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    normalized = empty_payload()

    for field in STRING_FIELDS:
        normalized[field] = normalize_whitespace(payload.get(field))

    for field in LIST_FIELDS:
        normalized[field] = _coerce_list(payload.get(field))

    normalized["ano_publicacao"] = parse_year(payload.get("ano_publicacao"))
    normalized["horizonte_temporal"] = parse_year(payload.get("horizonte_temporal"))
    normalized["aplicou_estudo_futuro"] = _coerce_bool(payload.get("aplicou_estudo_futuro"))

    return normalized

def merge_partial_payloads(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    if not payloads:
        return empty_payload()

    merged = empty_payload()

    for field in STRING_FIELDS:
        merged[field] = coalesce(*(payload.get(field) for payload in payloads))

    merged["ano_publicacao"] = coalesce(*(payload.get("ano_publicacao") for payload in payloads))
    merged["horizonte_temporal"] = coalesce(*(payload.get("horizonte_temporal") for payload in payloads))

    bool_values = [payload.get("aplicou_estudo_futuro") for payload in payloads if payload.get("aplicou_estudo_futuro") is not None]
    merged["aplicou_estudo_futuro"] = True if True in bool_values else (False if bool_values else None)

    for field in LIST_FIELDS:
        combined = []
        for payload in payloads:
            combined.extend(payload.get(field, []))
        merged[field] = union_unique_preserve_order(combined)

    return merged
