from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pandas as pd

from src.enrichment_ai.enrichment_prompts import (
    build_condicionante_prompt,
    build_institution_enrichment_prompt,
    build_method_taxonomy_prompt,
)
from src.enrichment_ai.hybrid_rules import (
    classify_condition_rule,
    classify_institution_rule,
    classify_method_rule,
    norm_text,
)
from src.enrichment_ai.llm_enrichment_client import EnrichmentClient
from src.shared.config import Settings
from src.shared.utils import to_json_string


def _read_unique_values(path: Path, logger: Any, preferred_col: str = "valor_original") -> list[str]:
    if not path.exists():
        logger.info(f"Arquivo não encontrado: {path}")
        return []
    df = pd.read_csv(path, encoding="utf-8-sig")
    if df.empty:
        return []
    if preferred_col in df.columns:
        series = df[preferred_col]
    elif "valor_original" in df.columns:
        series = df["valor_original"]
    else:
        series = df.iloc[:, 0]
    values = series.dropna().astype(str).str.strip()
    return sorted([v for v in values.unique().tolist() if v])


def _dedupe_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        value = str(value).strip()
        if not value:
            continue
        key = norm_text(value)
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return sorted(output, key=lambda x: norm_text(x))


def _safe_parse_list(value: Any) -> list[Any]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                return parsed if isinstance(parsed, list) else [parsed]
            except Exception:
                return [text]
        return [text]
    return [value]


def _read_institution_values(settings: Settings, logger: Any) -> list[str]:
    """Une instituições responsáveis e de apoio para gerar um único dicionário institucional."""
    values: list[str] = []

    # Responsáveis.
    values.extend(_read_unique_values(settings.transformed_unique_dir / "valores_unicos_instituicao_responsavel.csv", logger))

    # Tabela normalizada de instituições, com listas de apoio.
    path_norm = settings.transformed_normalized_dir / "instituicoes_normalizadas.csv"
    if path_norm.exists():
        df = pd.read_csv(path_norm, encoding="utf-8-sig")
        for col in ["instituicao_responsavel_normalizada", "instituicao_responsavel_original"]:
            if col in df.columns:
                values.extend(df[col].dropna().astype(str).str.strip().tolist())
        for col in ["instituicoes_apoio_normalizadas", "instituicoes_apoio_originais"]:
            if col in df.columns:
                for item in df[col].dropna().tolist():
                    values.extend([str(v).strip() for v in _safe_parse_list(item) if str(v).strip()])

    # Base consolidada normalizada, quando existir.
    for path in [
        settings.ai_applied_dir / "documentos_consolidados_normalizado_ia.csv",
        settings.transformed_base_dir / "documentos_consolidados.csv",
    ]:
        if path.exists():
            df = pd.read_csv(path, encoding="utf-8-sig")
            for col in ["instituicao_responsavel_norm", "instituicao_responsavel"]:
                if col in df.columns:
                    values.extend(df[col].dropna().astype(str).str.strip().tolist())
            for col in ["instituicoes_apoio_norm", "instituicoes_apoio"]:
                if col in df.columns:
                    for item in df[col].dropna().tolist():
                        values.extend([str(v).strip() for v in _safe_parse_list(item) if str(v).strip()])
            break

    return _dedupe_values(values)


def _read_method_values(settings: Settings, logger: Any) -> list[str]:
    candidates: list[str] = []

    path_norm = settings.transformed_normalized_dir / "metodos_normalizados.csv"
    if path_norm.exists():
        df = pd.read_csv(path_norm, encoding="utf-8-sig")
        for col in ["metodo_normalizado", "metodo_original"]:
            if col in df.columns:
                candidates.extend(df[col].dropna().astype(str).str.strip().tolist())

    for filename in ["valores_unicos_metodos.csv", "valores_unicos_metodos_estudo_futuro.csv"]:
        path_unique = settings.transformed_unique_dir / filename
        if path_unique.exists():
            candidates.extend(_read_unique_values(path_unique, logger))

    return _dedupe_values(candidates)


def _save_dataframe(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def _items_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    items = payload.get("items", [])
    return items if isinstance(items, list) else []


def _run_prompt_in_batches(
    values: list[str],
    prompt_builder,
    client: EnrichmentClient,
    settings: Settings,
    logger: Any,
    label: str,
) -> tuple[list[dict[str, Any]], str | None]:
    all_items: list[dict[str, Any]] = []
    last_model: str | None = None
    batch_size = max(1, int(settings.ai_dictionary_batch_size))
    total = (len(values) + batch_size - 1) // batch_size

    for idx in range(0, len(values), batch_size):
        batch = values[idx: idx + batch_size]
        batch_no = idx // batch_size + 1
        logger.info(f"Enrichment IA: {label} | lote {batch_no}/{total} | valores: {len(batch)}")
        payload, model_used = client.run(prompt_builder(batch))
        last_model = model_used
        all_items.extend(_items_from_payload(payload))
        time.sleep(settings.pause_between_calls)

    return all_items, last_model


def _hybrid_classify(
    values: list[str],
    rule_func,
    prompt_builder,
    client: EnrichmentClient,
    settings: Settings,
    logger: Any,
    label: str,
) -> tuple[pd.DataFrame, str | None]:
    rule_rows: list[dict[str, Any]] = []
    pending: list[str] = []

    for value in values:
        row = rule_func(value)
        if row is None:
            pending.append(value)
        else:
            rule_rows.append(row)

    logger.info(f"Enrichment híbrido: {label} | regras: {len(rule_rows)} | IA pendente: {len(pending)}")

    ai_rows: list[dict[str, Any]] = []
    model_used: str | None = None
    if pending:
        ai_rows, model_used = _run_prompt_in_batches(pending, prompt_builder, client, settings, logger, label)
        for row in ai_rows:
            row.setdefault("fonte_classificacao", "ia")
            row.setdefault("acao_recomendada", "revisar_manual" if row.get("confianca") == "baixa" else "aplicar_automatico")

    rows = rule_rows + ai_rows
    df = pd.DataFrame(rows)
    if not df.empty and "valor_original" in df.columns:
        df["_key"] = df["valor_original"].apply(norm_text)
        df = df.drop_duplicates(subset=["_key"], keep="last").drop(columns=["_key"])
    return df, model_used


def _ensure_categoria_compat(path: Path) -> None:
    if not path.exists():
        return
    df = pd.read_csv(path, encoding="utf-8-sig")
    if "categoria" not in df.columns and "categoria_steep" in df.columns:
        df["categoria"] = df["categoria_steep"]
    if "eh_condicionante_prospectivo" not in df.columns:
        df["eh_condicionante_prospectivo"] = "Revisar"
    df.to_csv(path, index=False, encoding="utf-8-sig")


def run_enrichment(settings: Settings, logger: Any) -> dict[str, Any]:
    client = EnrichmentClient(
        api_key=settings.gemini_api_key,
        model_simple=settings.model_simple,
        model_context=settings.model_context,
        max_retries=settings.max_retries,
        timeout_seconds=settings.llm_timeout_seconds,
        context_model_min_chars=settings.context_model_min_chars,
        logger=logger,
    )

    output = {"instituicoes": 0, "metodos": 0, "condicionantes": 0, "status": "ok"}

    # ============================================================
    # 1. ENRIQUECIMENTO HÍBRIDO DE INSTITUIÇÕES
    #    Usa responsáveis + apoio, não apenas responsáveis.
    # ============================================================
    values = _read_institution_values(settings, logger)
    if values:
        df, model_used = _hybrid_classify(
            values,
            classify_institution_rule,
            build_institution_enrichment_prompt,
            client,
            settings,
            logger,
            "instituicoes",
        )
        out_path = settings.enrichment_dir / "dicionario_instituicoes_enriquecido.csv"
        _save_dataframe(df, out_path)
        output["instituicoes"] = len(values)
        logger.info(f"Enriquecimento híbrido de instituições concluído. Valores: {len(values)} | modelo IA: {model_used or 'não usado'}")
    else:
        logger.info("Enriquecimento de instituições: nenhum valor encontrado.")

    # ============================================================
    # 2. TAXONOMIA HÍBRIDA DE MÉTODOS DE ESTUDOS DE FUTURO
    # ============================================================
    values = _read_method_values(settings, logger)
    if values:
        df, model_used = _hybrid_classify(
            values,
            classify_method_rule,
            build_method_taxonomy_prompt,
            client,
            settings,
            logger,
            "metodos",
        )
        out_path = settings.enrichment_dir / "dicionario_metodos_taxonomia.csv"
        _save_dataframe(df, out_path)
        output["metodos"] = len(values)
        logger.info(f"Taxonomia híbrida de métodos concluída. Valores: {len(values)} | modelo IA: {model_used or 'não usado'}")
    else:
        logger.info("Taxonomia de métodos: nenhum valor encontrado.")

    # ============================================================
    # 3. CLUSTERIZAÇÃO PROSPECTIVA HÍBRIDA DE CONDICIONANTES
    # ============================================================
    values = _read_unique_values(settings.transformed_unique_dir / "valores_unicos_condicionantes.csv", logger)
    if values:
        df, model_used = _hybrid_classify(
            values,
            classify_condition_rule,
            build_condicionante_prompt,
            client,
            settings,
            logger,
            "condicionantes",
        )
        out_path = settings.enrichment_dir / "dicionario_condicionantes_cluster.csv"
        _save_dataframe(df, out_path)
        _ensure_categoria_compat(out_path)
        output["condicionantes"] = len(values)
        logger.info(f"Clusterização prospectiva híbrida de condicionantes concluída. Valores: {len(values)} | modelo IA: {model_used or 'não usado'}")
    else:
        logger.info("Clusterização de condicionantes: nenhum valor encontrado.")

    return output
