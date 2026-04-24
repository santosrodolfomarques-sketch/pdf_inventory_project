from __future__ import annotations

from typing import Any

import pandas as pd

from src.enrichment_ai.enrichment_prompts import (
    build_condicionante_prompt,
    build_institution_enrichment_prompt,
)
from src.enrichment_ai.llm_enrichment_client import EnrichmentClient
from src.shared.config import Settings


def _read_unique_values(path, logger: Any) -> list[str]:
    if not path.exists():
        logger.info(f"Arquivo não encontrado: {path}")
        return []

    df = pd.read_csv(path)

    if df.empty:
        return []

    if "valor_original" in df.columns:
        series = df["valor_original"]
    else:
        series = df.iloc[:, 0]

    valores = (
        series
        .dropna()
        .astype(str)
        .str.strip()
    )

    return sorted([v for v in valores.unique().tolist() if v])


def _save_result(resultado: Any, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(resultado, dict):
        if "items" in resultado and isinstance(resultado["items"], list):
            df = pd.DataFrame(resultado["items"])
        elif "resultados" in resultado and isinstance(resultado["resultados"], list):
            df = pd.DataFrame(resultado["resultados"])
        else:
            df = pd.DataFrame([resultado])
    else:
        df = pd.DataFrame(resultado)

    df.to_csv(path, index=False, encoding="utf-8-sig")


def run_enrichment(settings: Settings, logger: Any) -> dict[str, Any]:
    client = EnrichmentClient(settings.gemini_api_key)

    output = {
        "instituicoes": 0,
        "condicionantes": 0,
        "status": "ok",
    }

    # ============================================================
    # 1. ENRIQUECIMENTO DE INSTITUIÇÕES
    # ============================================================
    instituicoes_path = settings.transformed_unique_dir / "valores_unicos_instituicao_responsavel.csv"
    valores_instituicoes = _read_unique_values(instituicoes_path, logger)

    if valores_instituicoes:
        prompt = build_institution_enrichment_prompt(valores_instituicoes)
        resultado = client.run(prompt, settings.model_flash)

        out_path = settings.enrichment_dir / "dicionario_instituicoes_enriquecido.csv"
        _save_result(resultado, out_path)

        output["instituicoes"] = len(valores_instituicoes)
        logger.info(f"Enriquecimento de instituições concluído. Valores: {len(valores_instituicoes)}")
    else:
        logger.info("Enriquecimento de instituições: nenhum valor encontrado.")

    # ============================================================
    # 2. CLUSTERIZAÇÃO DE CONDICIONANTES
    # ============================================================
    condicionantes_path = settings.transformed_unique_dir / "valores_unicos_condicionantes.csv"
    valores_condicionantes = _read_unique_values(condicionantes_path, logger)

    if valores_condicionantes:
        prompt = build_condicionante_prompt(valores_condicionantes)
        resultado = client.run(prompt, settings.model_flash)

        out_path = settings.enrichment_dir / "dicionario_condicionantes_cluster.csv"
        _save_result(resultado, out_path)

        output["condicionantes"] = len(valores_condicionantes)
        logger.info(f"Clusterização de condicionantes concluída. Valores: {len(valores_condicionantes)}")
    else:
        logger.info("Clusterização de condicionantes: nenhum valor encontrado.")

    return output