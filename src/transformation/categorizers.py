from __future__ import annotations

from collections import defaultdict
from typing import Any

def build_pending_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pending_rows: list[dict[str, Any]] = []

    for record in records:
        reasons = []

        if not record.get("nome_documento_norm"):
            reasons.append("nome_documento_ausente")
        if record.get("ano_publicacao") is None:
            reasons.append("ano_publicacao_ausente")
        if record.get("familia_do_metodo_norm") in (None, "Outros") and record.get("aplicou_estudo_futuro"):
            reasons.append("familia_do_metodo_revisar")
        if record.get("tipo_documento_norm") is None:
            reasons.append("tipo_documento_revisar")
        if record.get("abrangencia_territorial_norm") is None:
            reasons.append("abrangencia_revisar")

        if reasons:
            pending_rows.append({
                "id_documento_logico": record.get("id_documento_logico"),
                "nome_documento": record.get("nome_documento"),
                "arquivo_origem": record.get("source_file_name"),
                "motivos": " | ".join(reasons),
            })

    return pending_rows

def collect_unique_values(records: list[dict[str, Any]], field_name: str) -> list[dict[str, Any]]:
    values = defaultdict(set)

    for record in records:
        original = record.get(field_name)
        normalized = record.get(f"{field_name}_norm")

        if isinstance(original, list):
            for value in original:
                values[str(value)].add(str(normalized) if normalized is not None else "")
        else:
            values[str(original)].add(str(normalized) if normalized is not None else "")

    output = []
    for original, normalized_set in sorted(values.items()):
        output.append({
            "valor_original": "" if original == "None" else original,
            "valor_normalizado": " | ".join(sorted(item for item in normalized_set if item)),
        })
    return output
