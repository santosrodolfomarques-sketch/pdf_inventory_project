from __future__ import annotations

import json
import re
from typing import Any
from src.shared.schemas import normalize_payload

def _extract_first_json_candidate(text: str) -> str:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return text

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        return match.group(0)
    raise ValueError("Nenhum JSON foi identificado na resposta do modelo.")

def parse_model_json(text: str) -> dict[str, Any]:
    candidate = _extract_first_json_candidate(text)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        cleaned = candidate.replace("\\n", " ").replace("\\t", " ")
        cleaned = re.sub(r",\s*([}\]])", r"\\1", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc2:
            raise ValueError(f"Falha ao interpretar JSON do modelo: {exc2}") from exc

def validate_and_normalize_payload(raw_payload: dict[str, Any] | None) -> dict[str, Any]:
    return normalize_payload(raw_payload)
