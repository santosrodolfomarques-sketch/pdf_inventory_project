from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.shared.config import Settings
from src.shared.utils import read_json, to_json_string
from src.transformation.business_rules import apply_business_rules
from src.transformation.categorizers import build_pending_rows, collect_unique_values
from src.transformation.consolidation import consolidate_records
from src.transformation.deduplication import remove_exact_duplicates

LIST_COLUMNS = [
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


def _records_to_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for record in records:
        row = dict(record)
        for column in LIST_COLUMNS:
            if column in row:
                row[column] = to_json_string(row[column])
        rows.append(row)
    return pd.DataFrame(rows)


def _save_dataframe(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def _ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, list) else [parsed]
        except Exception:
            return [text]
    return [value]


def _build_unique_list_values_dataframe(records: list[dict[str, Any]], field: str, value_col: str = "valor_original") -> pd.DataFrame:
    rows = []
    for record in records:
        for value in _ensure_list(record.get(field)):
            if value is None:
                continue
            value_text = str(value).strip()
            if value_text:
                rows.append({value_col: value_text})
    if not rows:
        return pd.DataFrame(columns=[value_col])
    return pd.DataFrame(rows).drop_duplicates().sort_values(value_col).reset_index(drop=True)


def _build_exploded_mapping_dataframe(records: list[dict[str, Any]], original_field: str, normalized_field: str, original_col: str, normalized_col: str) -> pd.DataFrame:
    rows = []
    for record in records:
        originals = record.get(original_field, []) or []
        normalizeds = record.get(normalized_field, []) or []
        for index, value in enumerate(originals):
            rows.append({
                original_col: value,
                normalized_col: normalizeds[index] if index < len(normalizeds) else None,
                "arquivo_origem": record.get("source_file_name"),
                "id_documento_logico": record.get("id_documento_logico"),
            })
    return pd.DataFrame(rows)


def run_transformation(settings: Settings, logger: Any) -> dict[str, Any]:
    json_files = sorted(Path(settings.extracted_json_dir).glob("*.json"))

    if not json_files:
        logger.info("Nenhum JSON bruto encontrado para transformação.")
        return {"processed": 0, "status": "empty"}

    treated_records: list[dict[str, Any]] = []

    for json_path in json_files:
        raw_data = read_json(json_path)
        payload = raw_data.get("payload", {})
        metadata = raw_data.get("metadata", {})
        treated = apply_business_rules(payload, metadata, settings)
        treated_records.append(treated)

    treated_records = remove_exact_duplicates(treated_records)
    consolidated_records = consolidate_records(treated_records)

    base_df = _records_to_dataframe(treated_records)
    consolidated_df = _records_to_dataframe(consolidated_records)

    base_path = settings.transformed_base_dir / "documentos_tratados.csv"
    consolidated_path = settings.transformed_base_dir / "documentos_consolidados.csv"

    _save_dataframe(base_df, base_path)
    _save_dataframe(consolidated_df, consolidated_path)

    unique_scalar_fields = [
        "tipo_documento",
        "abrangencia_territorial",
        "setor",
        "instituicao_responsavel",
        "tipo_estudo_futuro",
    ]
    for field in unique_scalar_fields:
        unique_rows = collect_unique_values(consolidated_records, field)
        unique_df = pd.DataFrame(unique_rows)
        _save_dataframe(unique_df, settings.transformed_unique_dir / f"valores_unicos_{field}.csv")

    family_rows = [
        {
            "valor_original": record.get("familia_do_metodo") or "",
            "valor_normalizado": record.get("familia_do_metodo_norm") or "",
        }
        for record in consolidated_records
    ]
    _save_dataframe(pd.DataFrame(family_rows), settings.transformed_unique_dir / "valores_unicos_familia_do_metodo.csv")

    condicionantes_df = _build_unique_list_values_dataframe(
        consolidated_records,
        field="condicionantes_estudo_futuro",
        value_col="valor_original",
    )
    _save_dataframe(condicionantes_df, settings.transformed_unique_dir / "valores_unicos_condicionantes.csv")

    normalized_tables = {
        "temas_normalizados.csv": _build_exploded_mapping_dataframe(
            treated_records, "temas", "temas_norm", "tema_original", "tema_normalizado"
        ),
        "metodos_normalizados.csv": _build_exploded_mapping_dataframe(
            treated_records, "metodos_estudo_futuro", "metodos_estudo_futuro_norm", "metodo_original", "metodo_normalizado"
        ),
        "instituicoes_normalizadas.csv": pd.DataFrame(
            [
                {
                    "instituicao_responsavel_original": row.get("instituicao_responsavel"),
                    "instituicao_responsavel_normalizada": row.get("instituicao_responsavel_norm"),
                    "instituicoes_apoio_originais": to_json_string(row.get("instituicoes_apoio")),
                    "instituicoes_apoio_normalizadas": to_json_string(row.get("instituicoes_apoio_norm")),
                    "arquivo_origem": row.get("source_file_name"),
                    "id_documento_logico": row.get("id_documento_logico"),
                }
                for row in treated_records
            ]
        ),
        "condicionantes_normalizados.csv": _build_unique_list_values_dataframe(
            consolidated_records,
            field="condicionantes_estudo_futuro",
            value_col="condicionante",
        ),
    }

    for filename, df in normalized_tables.items():
        _save_dataframe(df, settings.transformed_normalized_dir / filename)

    pending_rows = build_pending_rows(consolidated_records)
    pending_df = pd.DataFrame(pending_rows)
    _save_dataframe(pending_df, settings.transformed_pending_dir / "pendencias_classificacao.csv")

    summary = {
        "processed": len(treated_records),
        "consolidated": len(consolidated_records),
        "status": "ok",
        "base_path": str(base_path),
        "consolidated_path": str(consolidated_path),
    }
    logger.info(
        f"Transformação concluída. Registros tratados: {summary['processed']} | consolidados: {summary['consolidated']}"
    )
    return summary
