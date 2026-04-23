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
        "familia_do_metodo",
        "instituicao_responsavel",
    ]
    for field in unique_scalar_fields:
        unique_rows = collect_unique_values(consolidated_records, field)
        unique_df = pd.DataFrame(unique_rows)
        _save_dataframe(unique_df, settings.transformed_unique_dir / f"valores_unicos_{field}.csv")

    normalized_tables = {
        "temas_normalizados.csv": pd.DataFrame(
            [{"tema_original": row.get("temas"), "tema_normalizado": row.get("temas_norm")} for row in treated_records]
        ),
        "metodos_normalizados.csv": pd.DataFrame(
            [{"metodo_original": row.get("metodos_estudo_futuro"), "metodo_normalizado": row.get("metodos_estudo_futuro_norm")} for row in treated_records]
        ),
        "instituicoes_normalizadas.csv": pd.DataFrame(
            [{
                "instituicao_responsavel_original": row.get("instituicao_responsavel"),
                "instituicao_responsavel_normalizada": row.get("instituicao_responsavel_norm"),
                "instituicoes_apoio_originais": to_json_string(row.get("instituicoes_apoio")),
                "instituicoes_apoio_normalizadas": to_json_string(row.get("instituicoes_apoio_norm")),
            } for row in treated_records]
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
    logger.info(f"Transformação concluída. Registros tratados: {summary['processed']} | consolidados: {summary['consolidated']}")
    return summary
