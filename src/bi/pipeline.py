from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.bi.star_schema import build_star_schema
from src.bi.validators import run_bi_validations
from src.core.config import Settings


def _save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def run_bi_preparation(settings: Settings, logger: Any) -> dict[str, Any]:
    """Orquestra a geração completa do Star Schema para BI e valida as chaves estruturadas."""
    ai_consolidated_path = settings.ai_applied_dir / "documentos_consolidados_normalizado_ia.csv"
    consolidated_path = (
        ai_consolidated_path
        if ai_consolidated_path.exists()
        else settings.transformed_base_dir / "documentos_consolidados.csv"
    )

    if not consolidated_path.exists():
        logger.error("Arquivo consolidado não encontrado. Execute a transformação inicial primeiro.")
        return {"processed": 0, "status": "missing_transformed"}

    logger.info(f"Carregando dados consolidados de: {consolidated_path.name}")
    df = pd.read_csv(consolidated_path)

    # Constrói o modelo de BI
    star_schema = build_star_schema(df, settings)
    fact = star_schema.pop("fato_inventario")

    # Separa dimensões e pontes para salvar em caminhos organizados
    dimensions = {}
    for name, dataframe in star_schema.items():
        if name.startswith("dim_"):
            _save_csv(dataframe, settings.bi_dim_dir / f"{name}.csv")
            dimensions[name] = dataframe
        elif name.startswith("ponte_"):
            _save_csv(dataframe, settings.bi_bridge_dir / f"{name}.csv")
            dimensions[name] = dataframe

    _save_csv(fact, settings.bi_fact_dir / "fato_inventario.csv")

    # Validação estrutural de chaves estrangeiras e integridade referencial
    logger.info("Executando validações estruturais de integridade de chaves no Star Schema...")
    validation_report = run_bi_validations(dimensions, fact, source=df)

    # Gravação do Dicionário de Dados
    dictionary_meta = {
        "dimensoes": sorted([name for name in dimensions if name.startswith("dim_")]),
        "pontes": sorted([name for name in dimensions if name.startswith("ponte_")]),
        "fato": "fato_inventario",
        "validacao": validation_report,
    }

    dict_path = settings.bi_dict_dir / "dicionario_dados.json"
    dict_path.parent.mkdir(parents=True, exist_ok=True)
    with dict_path.open("w", encoding="utf-8") as handle:
        json.dump(dictionary_meta, handle, ensure_ascii=False, indent=2)

    logger.info(f"Modelagem Estrela BI gerada com sucesso. Resultados salvos em: {settings.bi_fact_dir.parent}")
    return {
        "processed": len(fact),
        "status": "ok" if validation_report["status"] != "error" else "validation_error",
        "fact_path": str(settings.bi_fact_dir / "fato_inventario.csv"),
        "dictionary_path": str(dict_path),
    }
