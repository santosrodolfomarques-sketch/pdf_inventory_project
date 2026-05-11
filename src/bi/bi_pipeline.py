from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.bi.dimensions import build_dimensions_and_bridges
from src.bi.facts import build_fact_inventory
from src.bi.validators import run_bi_validations
from src.shared.config import Settings

def _save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")

def run_bi_preparation(settings: Settings, logger: Any) -> dict[str, Any]:
    ai_consolidated_path = settings.ai_applied_dir / "documentos_consolidados_normalizado_ia.csv"
    consolidated_path = ai_consolidated_path if ai_consolidated_path.exists() else settings.transformed_base_dir / "documentos_consolidados.csv"

    if not consolidated_path.exists():
        logger.info("Arquivo consolidado não encontrado. Execute a transformação antes do BI.")
        return {"processed": 0, "status": "missing_transformed"}

    df = pd.read_csv(consolidated_path)
    dimensions = build_dimensions_and_bridges(df, settings=settings)
    fact = build_fact_inventory(df, dimensions)
    validation_report = run_bi_validations(dimensions, fact, source=df)

    for name, dataframe in dimensions.items():
        if name.startswith("dim_"):
            _save_csv(dataframe, settings.bi_dim_dir / f"{name}.csv")
        elif name.startswith("ponte_"):
            _save_csv(dataframe, settings.bi_bridge_dir / f"{name}.csv")

    _save_csv(fact, settings.bi_fact_dir / "fato_inventario.csv")

    dictionary = {
        "dimensoes": sorted([name for name in dimensions if name.startswith("dim_")]),
        "pontes": sorted([name for name in dimensions if name.startswith("ponte_")]),
        "fato": "fato_inventario",
        "validacao": validation_report,
    }

    dict_path = settings.bi_dict_dir / "dicionario_dados.json"
    dict_path.parent.mkdir(parents=True, exist_ok=True)
    with dict_path.open("w", encoding="utf-8") as handle:
        json.dump(dictionary, handle, ensure_ascii=False, indent=2)

    logger.info("Preparação para BI concluída.")
    return {
        "processed": len(fact),
        "status": "ok" if validation_report["status"] != "error" else "validation_error",
        "fact_path": str(settings.bi_fact_dir / "fato_inventario.csv"),
        "dictionary_path": str(dict_path),
    }
