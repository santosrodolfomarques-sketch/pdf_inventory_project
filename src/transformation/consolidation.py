from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.shared.ids import stable_hash_id
from src.shared.utils import coalesce, union_unique_preserve_order

LIST_FIELDS = [
    "temas",
    "temas_norm",
    "metodos_estudo_futuro",
    "metodos_estudo_futuro_norm",
    "referencias",
    "condicionantes_estudo_futuro",
    "instituicoes_apoio",
    "instituicoes_apoio_norm",
    "source_files",
]

def build_logical_document_id(record: dict[str, Any]) -> str:
    return stable_hash_id(
        "doc",
        record.get("nome_documento_norm") or record.get("nome_documento"),
        record.get("instituicao_responsavel_norm") or record.get("instituicao_responsavel"),
        record.get("ano_publicacao"),
    )

def consolidate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for record in records:
        logical_id = record.get("id_documento_logico") or build_logical_document_id(record)
        record["id_documento_logico"] = logical_id
        grouped[logical_id].append(record)

    consolidated: list[dict[str, Any]] = []

    for logical_id, group in grouped.items():
        base = dict(group[0])
        base["id_documento_logico"] = logical_id
        base["qtd_arquivos_origem"] = len(group)
        base["source_files"] = [item.get("source_file_name") for item in group if item.get("source_file_name")]

        for field in LIST_FIELDS:
            aggregated = []
            for item in group:
                aggregated.extend(item.get(field, []))
            base[field] = union_unique_preserve_order(aggregated)

        scalar_fields = [
            "nome_documento",
            "nome_documento_norm",
            "tipo_documento",
            "tipo_documento_norm",
            "ano_publicacao",
            "horizonte_temporal",
            "extensao_tempo",
            "abrangencia_territorial",
            "abrangencia_territorial_norm",
            "setor",
            "setor_norm",
            "aplicou_estudo_futuro",
            "tipo_estudo_futuro",
            "familia_do_metodo",
            "familia_do_metodo_norm",
            "instituicao_responsavel",
            "instituicao_responsavel_norm",
            "sigla_ou_abreviacao",
        ]

        for field in scalar_fields:
            base[field] = coalesce(*(item.get(field) for item in group))

        consolidated.append(base)

    return consolidated
