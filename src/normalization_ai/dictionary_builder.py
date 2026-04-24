from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd

from src.normalization_ai.dictionary_validator import validate_dictionary_items
from src.normalization_ai.llm_normalizer_client import GeminiDictionaryClient
from src.normalization_ai.normalization_prompts import build_dictionary_prompt
from src.shared.config import Settings
from src.shared.utils import remove_accents_lower


def _read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def _value_rows_from_dataframe(df: pd.DataFrame, value_col: str, normalized_col: str | None = None, count_col: str | None = None) -> list[dict[str, Any]]:
    if df.empty or value_col not in df.columns:
        return []

    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        value = row.get(value_col)
        if pd.isna(value) or str(value).strip() == "":
            continue
        item: dict[str, Any] = {"valor_original": str(value).strip()}
        if normalized_col and normalized_col in df.columns and not pd.isna(row.get(normalized_col)):
            item["valor_normalizado_atual"] = str(row.get(normalized_col)).strip()
        if count_col and count_col in df.columns and not pd.isna(row.get(count_col)):
            item["frequencia"] = row.get(count_col)
        rows.append(item)

    return rows


def _deduplicate_value_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for item in rows:
        key = remove_accents_lower(item.get("valor_original"))
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def _load_target_values(settings: Settings, target_name: str) -> list[dict[str, Any]]:
    unique_dir = settings.transformed_unique_dir
    normalized_dir = settings.transformed_normalized_dir

    if target_name in {"setor", "tipo_documento", "abrangencia_territorial", "tipo_estudo_futuro", "familia_do_metodo"}:
        path = unique_dir / f"valores_unicos_{target_name}.csv"
        df = _read_csv_if_exists(path)
        # A função collect_unique_values costuma gerar valor_original, valor_normalizado e frequencia.
        value_col = "valor_original" if "valor_original" in df.columns else df.columns[0] if len(df.columns) else ""
        normalized_col = "valor_normalizado" if "valor_normalizado" in df.columns else None
        count_col = "frequencia" if "frequencia" in df.columns else None
        return _deduplicate_value_rows(_value_rows_from_dataframe(df, value_col, normalized_col, count_col))

    if target_name == "temas":
        df = _read_csv_if_exists(normalized_dir / "temas_normalizados.csv")
        return _deduplicate_value_rows(_value_rows_from_dataframe(df, "tema_original", "tema_normalizado"))

    if target_name == "metodos":
        df = _read_csv_if_exists(normalized_dir / "metodos_normalizados.csv")
        return _deduplicate_value_rows(_value_rows_from_dataframe(df, "metodo_original", "metodo_normalizado"))

    if target_name == "instituicoes":
        df = _read_csv_if_exists(normalized_dir / "instituicoes_normalizadas.csv")
        rows: list[dict[str, Any]] = []
        if not df.empty:
            rows.extend(_value_rows_from_dataframe(df, "instituicao_responsavel_original", "instituicao_responsavel_normalizada"))
            # As instituições de apoio estão em JSON string. Vamos extrair valores de forma simples.
            for _, row in df.iterrows():
                raw = row.get("instituicoes_apoio_originais")
                norm = row.get("instituicoes_apoio_normalizadas")
                if pd.isna(raw) or str(raw).strip() in {"", "[]"}:
                    continue
                try:
                    import json
                    raw_values = json.loads(raw)
                    norm_values = json.loads(norm) if not pd.isna(norm) and str(norm).strip() else []
                except Exception:
                    raw_values = []
                    norm_values = []
                for index, value in enumerate(raw_values):
                    if not value:
                        continue
                    item = {"valor_original": str(value).strip()}
                    if index < len(norm_values) and norm_values[index]:
                        item["valor_normalizado_atual"] = str(norm_values[index]).strip()
                    rows.append(item)
        return _deduplicate_value_rows(rows)

    raise ValueError(f"Target de normalização desconhecido: {target_name}")


def _chunk(values: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    return [values[i:i + batch_size] for i in range(0, len(values), batch_size)]


def build_ai_dictionaries(
    settings: Settings,
    logger: Any,
    *,
    targets: list[str] | None = None,
    only_new_values: bool = False,
) -> dict[str, Any]:
    targets = targets or [
        "setor",
        "tipo_documento",
        "abrangencia_territorial",
        "tipo_estudo_futuro",
        "familia_do_metodo",
        "temas",
        "metodos",
        "instituicoes",
    ]

    settings.ai_dictionary_dir.mkdir(parents=True, exist_ok=True)
    settings.ai_dictionary_review_dir.mkdir(parents=True, exist_ok=True)

    client = GeminiDictionaryClient(
        api_key=settings.gemini_api_key,
        model_flash=settings.model_flash,
        model_pro=settings.model_pro,
        max_retries=settings.max_retries,
        logger=logger,
    )

    summary: dict[str, Any] = {"targets": {}, "status": "ok"}

    for target in targets:
        values = _load_target_values(settings, target)
        out_path = settings.ai_dictionary_dir / f"dicionario_{target}.csv"

        if only_new_values and out_path.exists():
            existing = pd.read_csv(out_path, encoding="utf-8-sig")
            existing_keys = set(existing.get("valor_original_limpo", pd.Series(dtype=str)).dropna().astype(str))
            values = [item for item in values if remove_accents_lower(item.get("valor_original")) not in existing_keys]

        if not values:
            logger.info(f"Normalização IA: nenhum valor novo para {target}.")
            summary["targets"][target] = {"values": 0, "batches": 0, "path": str(out_path)}
            continue

        all_frames: list[pd.DataFrame] = []
        batches = _chunk(values, settings.ai_dictionary_batch_size)
        for batch_index, batch in enumerate(batches, start=1):
            logger.info(f"Normalização IA: {target} | lote {batch_index}/{len(batches)} | valores: {len(batch)}")
            prompt = build_dictionary_prompt(target_name=target, values=batch)
            payload = client.generate_dictionary(prompt)
            df = validate_dictionary_items(
                target_name=target,
                items=payload.get("items", []),
                min_confidence=settings.ai_apply_min_confidence,
            )
            df["lote"] = batch_index
            all_frames.append(df)

        result_df = pd.concat(all_frames, ignore_index=True) if all_frames else pd.DataFrame()

        if only_new_values and out_path.exists() and not result_df.empty:
            old_df = pd.read_csv(out_path, encoding="utf-8-sig")
            result_df = pd.concat([old_df, result_df], ignore_index=True)
            result_df = result_df.drop_duplicates(subset=["campo", "valor_original_limpo"], keep="last")

        result_df.to_csv(out_path, index=False, encoding="utf-8-sig")

        review_df = result_df[result_df["aplicar_automaticamente"] != True].copy() if not result_df.empty else result_df
        review_path = settings.ai_dictionary_review_dir / f"revisar_{target}.csv"
        review_df.to_csv(review_path, index=False, encoding="utf-8-sig")

        summary["targets"][target] = {
            "values": len(values),
            "batches": len(batches),
            "path": str(out_path),
            "review_path": str(review_path),
        }

    logger.info("Normalização IA concluída.")
    return summary
