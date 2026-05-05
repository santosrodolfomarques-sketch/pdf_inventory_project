from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.normalization_ai.dictionary_validator import validate_dictionary_items
from src.normalization_ai.llm_normalizer_client import GeminiDictionaryClient
from src.normalization_ai.normalization_prompts import build_dictionary_prompt
from src.shared.config import Settings
from src.shared.ids import stable_hash_id
from src.shared.utils import remove_accents_lower, utc_now_iso, write_json, read_json


def _read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def _append_rows_to_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    fieldnames = list(rows[0].keys())
    with path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


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
            for _, row in df.iterrows():
                raw = row.get("instituicoes_apoio_originais")
                norm = row.get("instituicoes_apoio_normalizadas")
                if pd.isna(raw) or str(raw).strip() in {"", "[]"}:
                    continue
                try:
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


def _batch_key(target: str, batch: list[dict[str, Any]]) -> str:
    canonical = json.dumps(batch, ensure_ascii=False, sort_keys=True)
    return stable_hash_id("aib", target, canonical)


def _batch_cache_path(settings: Settings, target: str, batch_index: int, batch_key: str) -> Path:
    return settings.ai_batch_cache_dir / target / f"{batch_index:04d}__{batch_key}.json"


def _load_batch_cache(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return read_json(path)
    except Exception:
        return None


def _save_batch_cache(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, payload)


def _already_processed_keys(out_path: Path) -> set[str]:
    if not out_path.exists():
        return set()
    existing = pd.read_csv(out_path, encoding="utf-8-sig")
    if "valor_original_limpo" not in existing.columns:
        return set()
    return set(existing["valor_original_limpo"].dropna().astype(str))


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
    settings.ai_batch_cache_dir.mkdir(parents=True, exist_ok=True)
    settings.ai_control_dir.mkdir(parents=True, exist_ok=True)

    client = GeminiDictionaryClient(
        api_key=settings.gemini_api_key,
        model_flash=settings.model_simple,
        model_pro=settings.model_context,
        max_retries=settings.max_retries,
        logger=logger,
        timeout_seconds=settings.llm_timeout_seconds,
        context_model_min_chars=settings.context_model_min_chars,
    )

    summary: dict[str, Any] = {"targets": {}, "status": "ok"}
    control_csv = settings.ai_control_dir / "controle_normalizacao_ia.csv"

    for target in targets:
        values = _load_target_values(settings, target)
        out_path = settings.ai_dictionary_dir / f"dicionario_{target}.csv"

        if (only_new_values or settings.ai_dictionary_resume) and out_path.exists():
            existing_keys = _already_processed_keys(out_path)
            values = [item for item in values if remove_accents_lower(item.get("valor_original")) not in existing_keys]

        if not values:
            logger.info(f"Normalização IA: nenhum valor novo para {target}.")
            summary["targets"][target] = {"values": 0, "batches": 0, "path": str(out_path)}
            continue

        batches = _chunk(values, settings.ai_dictionary_batch_size)
        batch_frames: list[pd.DataFrame] = []

        for batch_index, batch in enumerate(batches, start=1):
            batch_key = _batch_key(target, batch)
            cache_path = _batch_cache_path(settings, target, batch_index, batch_key)
            logger.info(f"Normalização IA: {target} | lote {batch_index}/{len(batches)} | valores: {len(batch)}")

            payload: dict[str, Any] | None = None
            model_used = ""
            status = "success"
            error = ""

            if settings.ai_dictionary_resume and not settings.ai_dictionary_force_reprocess:
                cached = _load_batch_cache(cache_path)
                if cached and isinstance(cached.get("payload"), dict):
                    payload = cached["payload"]
                    model_used = cached.get("model_used", "cache")
                    logger.info(f"Normalização IA: cache de lote reutilizado para {target} lote {batch_index}.")

            if payload is None:
                try:
                    prompt = build_dictionary_prompt(target_name=target, values=batch)
                    payload, model_used = client.generate_dictionary(prompt)
                    _save_batch_cache(cache_path, {
                        "target": target,
                        "batch_index": batch_index,
                        "batch_key": batch_key,
                        "model_used": model_used,
                        "created_at_utc": utc_now_iso(),
                        "values": batch,
                        "payload": payload,
                    })
                except Exception as exc:
                    status = "failed"
                    error = str(exc)
                    logger.exception(f"Normalização IA falhou em {target} lote {batch_index}: {exc}")
                    _append_rows_to_csv(control_csv, [{
                        "timestamp_utc": utc_now_iso(),
                        "target": target,
                        "batch_index": batch_index,
                        "batch_key": batch_key,
                        "status": status,
                        "model_used": model_used,
                        "cache_path": str(cache_path),
                        "erro": error,
                    }])
                    continue

            try:
                df = validate_dictionary_items(
                    target_name=target,
                    items=payload.get("items", []),
                    min_confidence=settings.ai_apply_min_confidence,
                )
                df["lote"] = batch_index
                df["batch_key"] = batch_key
                df["model_used"] = model_used
                batch_frames.append(df)
            except Exception as exc:
                status = "failed_validation"
                error = str(exc)
                logger.exception(f"Validação de dicionário falhou em {target} lote {batch_index}: {exc}")

            _append_rows_to_csv(control_csv, [{
                "timestamp_utc": utc_now_iso(),
                "target": target,
                "batch_index": batch_index,
                "batch_key": batch_key,
                "status": status,
                "model_used": model_used,
                "cache_path": str(cache_path),
                "erro": error,
            }])

        new_df = pd.concat(batch_frames, ignore_index=True) if batch_frames else pd.DataFrame()
        if out_path.exists():
            old_df = pd.read_csv(out_path, encoding="utf-8-sig")
            result_df = pd.concat([old_df, new_df], ignore_index=True) if not new_df.empty else old_df
            if not result_df.empty and {"campo", "valor_original_limpo"}.issubset(result_df.columns):
                result_df = result_df.drop_duplicates(subset=["campo", "valor_original_limpo"], keep="last")
        else:
            result_df = new_df

        result_df.to_csv(out_path, index=False, encoding="utf-8-sig")

        review_df = result_df[result_df["aplicar_automaticamente"] != True].copy() if not result_df.empty and "aplicar_automaticamente" in result_df.columns else result_df
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
