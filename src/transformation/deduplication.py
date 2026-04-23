from __future__ import annotations

from typing import Any

def remove_exact_duplicates(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    output = []

    for record in records:
        key = (
            record.get("source_file_hash"),
            record.get("nome_documento_norm"),
            record.get("ano_publicacao"),
            record.get("instituicao_responsavel_norm"),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(record)

    return output
