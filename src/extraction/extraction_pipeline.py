from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any

from src.extraction.cache_manager import build_cache_path, load_cached_extraction, save_cached_extraction
from src.extraction.chunking import chunk_text
from src.extraction.llm_client import GeminiLLMClient
from src.extraction.pdf_reader import extract_text_pdf
from src.extraction.prompt_builder import build_extraction_prompt
from src.extraction.schema_validator import validate_and_normalize_payload
from src.shared.config import Settings
from src.shared.schemas import merge_partial_payloads
from src.shared.utils import append_rows_to_csv, file_sha256, read_json, utc_now_iso, write_json

FAILED_STATUSES = {
    "failed_no_text",
    "failed_llm",
    "failed_api",
    "failed_json",
    "failed_unexpected",
    "partial_failed",
}
SUCCESS_STATUSES = {"success", "cache_hit", "skipped_success"}


def _partial_path(cache_path: Path) -> Path:
    return cache_path.with_suffix(".partial.json")


def _load_partial(partial_path: Path) -> dict[str, Any] | None:
    if not partial_path.exists():
        return None
    try:
        return read_json(partial_path)
    except Exception:
        return None


def _save_partial(partial_path: Path, data: dict[str, Any]) -> None:
    write_json(partial_path, data)


def _read_latest_control_status(control_csv: Path) -> dict[str, str]:
    """Lê o último status conhecido por hash de arquivo."""
    if not control_csv.exists():
        return {}

    latest: dict[str, str] = {}
    try:
        with control_csv.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                file_hash = row.get("arquivo_hash") or ""
                status = row.get("status") or ""
                if file_hash:
                    latest[file_hash] = status
    except Exception:
        return {}
    return latest


def _control_row(
    *,
    pdf_path: Path,
    file_hash: str,
    status: str,
    cache_path: Path,
    model_used: str = "",
    chunks_total: int = 0,
    chunks_processed: int = 0,
    error: str = "",
    partial_path: Path | None = None,
) -> dict[str, Any]:
    return {
        "timestamp_utc": utc_now_iso(),
        "arquivo": pdf_path.name,
        "arquivo_hash": file_hash,
        "status": status,
        "modelo_utilizado": model_used,
        "chunks_total": chunks_total,
        "chunks_processados": chunks_processed,
        "cache_path": str(cache_path),
        "partial_path": str(partial_path or ""),
        "erro": error,
    }


def run_extraction(
    settings: Settings,
    logger: Any,
    force_reprocess: bool = False,
    only_failed: bool = False,
    limit: int | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    """
    Executa a extração de forma resiliente.

    Características:
    - salva JSON final imediatamente após cada PDF bem-sucedido;
    - salva checkpoint parcial por chunk para PDFs longos;
    - não interrompe o lote se um PDF falhar;
    - em --only-failed, reprocessa apenas arquivos cujo último status no controle foi falha;
    - reutiliza cache quando disponível, salvo quando force_reprocess=True.
    """
    all_pdf_files = sorted(Path(settings.raw_pdf_dir).glob("*.pdf"))
    pdf_files = all_pdf_files[offset:] if offset else all_pdf_files
    if limit is not None:
        pdf_files = pdf_files[:limit]
    control_rows: list[dict[str, Any]] = []
    control_csv = settings.extraction_control_dir / "controle_extracao.csv"
    latest_status = _read_latest_control_status(control_csv)

    if not pdf_files:
        logger.info("Nenhum PDF encontrado para extração.")
        return {"processed": 0, "status": "empty"}

    client = GeminiLLMClient(
        api_key=settings.gemini_api_key,
        model_flash=settings.model_flash,
        model_pro=settings.model_pro,
        max_retries=settings.max_retries,
        logger=logger,
        timeout_seconds=settings.llm_timeout_seconds,
        context_model_min_chars=settings.context_model_min_chars,
    )

    processed_count = 0
    failed_count = 0
    skipped_count = 0

    for index, pdf_path in enumerate(pdf_files, start=1):
        logger.info(f"[{index}/{len(pdf_files)}] Processando extração: {pdf_path.name}")
        try:
            file_hash = file_sha256(pdf_path)
        except Exception as exc:
            logger.exception(f"Falha ao calcular hash de {pdf_path.name}: {exc}")
            failed_count += 1
            continue

        last_status = latest_status.get(file_hash)
        cache_path = build_cache_path(settings.extracted_json_dir, pdf_path.stem, file_hash)
        partial_path = _partial_path(cache_path)

        if only_failed and last_status not in FAILED_STATUSES:
            logger.info(f"Pulando {pdf_path.name}: último status não é falha ({last_status or 'sem_status'}).")
            skipped_count += 1
            continue

        cached = None if force_reprocess else load_cached_extraction(cache_path)
        if cached:
            logger.info("Cache encontrado. Extração reutilizada.")
            control_rows.append(_control_row(
                pdf_path=pdf_path,
                file_hash=file_hash,
                status="cache_hit",
                model_used=cached.get("metadata", {}).get("model_used", ""),
                chunks_total=int(cached.get("metadata", {}).get("chunk_count", 0) or 0),
                chunks_processed=len(cached.get("chunk_payloads", [])),
                cache_path=cache_path,
            ))
            processed_count += 1
            continue

        try:
            text, extraction_meta = extract_text_pdf(
                pdf_path,
                max_pages_begin=settings.max_pages_begin,
                max_pages_end=settings.max_pages_end,
            )
        except Exception as exc:
            logger.exception(f"Falha inesperada ao ler PDF {pdf_path.name}: {exc}")
            control_rows.append(_control_row(
                pdf_path=pdf_path,
                file_hash=file_hash,
                status="failed_unexpected",
                cache_path=cache_path,
                error=str(exc),
            ))
            failed_count += 1
            continue

        if not text:
            logger.warning(f"Texto não extraído para {pdf_path.name}.")
            control_rows.append(_control_row(
                pdf_path=pdf_path,
                file_hash=file_hash,
                status="failed_no_text",
                cache_path=cache_path,
                error=extraction_meta.get("error", "texto_vazio"),
            ))
            failed_count += 1
            continue

        chunks = chunk_text(text, settings.max_chars_per_chunk, settings.chunk_overlap)
        partial = None if force_reprocess else _load_partial(partial_path)
        chunk_payloads: list[dict[str, Any]] = []
        models_used: list[str] = []

        if partial and partial.get("metadata", {}).get("source_file_hash") == file_hash:
            chunk_payloads = list(partial.get("chunk_payloads", []))
            models_used = list(partial.get("models_used", []))
            logger.info(
                f"Checkpoint parcial encontrado para {pdf_path.name}: "
                f"{len(chunk_payloads)}/{len(chunks)} chunks já concluídos."
            )

        try:
            start_chunk = len(chunk_payloads) + 1
            for chunk_number, chunk in enumerate(chunks[start_chunk - 1:], start=start_chunk):
                logger.info(f"Consultando LLM para chunk {chunk_number}/{len(chunks)} de {pdf_path.name}")
                prompt = build_extraction_prompt(chunk)
                raw_payload, model_used = client.generate_json(prompt)
                normalized_payload = validate_and_normalize_payload(raw_payload)
                chunk_payloads.append(normalized_payload)
                models_used.append(model_used)

                _save_partial(partial_path, {
                    "metadata": {
                        "source_file_name": pdf_path.name,
                        "source_file_path": str(pdf_path),
                        "source_file_hash": file_hash,
                        "processed_at_utc": utc_now_iso(),
                        "chunk_count": len(chunks),
                        "chunks_completed": len(chunk_payloads),
                        "extraction_details": extraction_meta,
                    },
                    "models_used": models_used,
                    "chunk_payloads": chunk_payloads,
                })

                time.sleep(settings.pause_between_calls)

            merged_payload = merge_partial_payloads(chunk_payloads)
            record = {
                "metadata": {
                    "source_file_name": pdf_path.name,
                    "source_file_path": str(pdf_path),
                    "source_file_hash": file_hash,
                    "processed_at_utc": utc_now_iso(),
                    "model_used": " | ".join(sorted(set(models_used))),
                    "chunk_count": len(chunks),
                    "extraction_details": extraction_meta,
                },
                "payload": merged_payload,
                "chunk_payloads": chunk_payloads,
            }

            save_cached_extraction(cache_path, record)
            if partial_path.exists():
                partial_path.unlink()
            processed_count += 1

            control_rows.append(_control_row(
                pdf_path=pdf_path,
                file_hash=file_hash,
                status="success",
                model_used=record["metadata"]["model_used"],
                chunks_total=len(chunks),
                chunks_processed=len(chunk_payloads),
                cache_path=cache_path,
            ))

        except Exception as exc:
            logger.exception(f"Falha ao extrair {pdf_path.name}: {exc}")
            failed_count += 1
            control_rows.append(_control_row(
                pdf_path=pdf_path,
                file_hash=file_hash,
                status="partial_failed" if chunk_payloads else "failed_llm",
                chunks_total=len(chunks),
                chunks_processed=len(chunk_payloads),
                cache_path=cache_path,
                partial_path=partial_path if chunk_payloads else None,
                error=str(exc),
            ))

        # Salva o controle a cada arquivo, para não perder histórico se o processo for interrompido.
        append_rows_to_csv(control_csv, control_rows)
        control_rows.clear()

    append_rows_to_csv(control_csv, control_rows)
    logger.info(f"Extração concluída. Controle salvo em: {control_csv}")
    return {
        "processed": processed_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "status": "ok" if failed_count == 0 else "warning",
        "control_csv": str(control_csv),
    }
