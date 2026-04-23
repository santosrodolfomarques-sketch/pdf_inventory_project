from __future__ import annotations

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
from src.shared.utils import append_rows_to_csv, file_sha256, utc_now_iso

def run_extraction(settings: Settings, logger: Any, force_reprocess: bool = False) -> dict[str, Any]:
    pdf_files = sorted(Path(settings.raw_pdf_dir).glob("*.pdf"))
    control_rows: list[dict[str, Any]] = []

    if not pdf_files:
        logger.info("Nenhum PDF encontrado para extração.")
        return {"processed": 0, "status": "empty"}

    client = GeminiLLMClient(
        api_key=settings.gemini_api_key,
        model_flash=settings.model_flash,
        model_pro=settings.model_pro,
        max_retries=settings.max_retries,
        logger=logger,
    )

    processed_count = 0

    for index, pdf_path in enumerate(pdf_files, start=1):
        logger.info(f"[{index}/{len(pdf_files)}] Processando extração: {pdf_path.name}")
        file_hash = file_sha256(pdf_path)
        cache_path = build_cache_path(settings.extracted_json_dir, pdf_path.stem, file_hash)
        cached = None if force_reprocess else load_cached_extraction(cache_path)

        if cached:
            logger.info("Cache encontrado. Extração reutilizada.")
            control_rows.append({
                "timestamp_utc": utc_now_iso(),
                "arquivo": pdf_path.name,
                "arquivo_hash": file_hash,
                "status": "cache_hit",
                "modelo_utilizado": cached.get("metadata", {}).get("model_used"),
                "chunks_processados": len(cached.get("chunk_payloads", [])),
                "cache_path": str(cache_path),
                "erro": "",
            })
            processed_count += 1
            continue

        text, extraction_meta = extract_text_pdf(
            pdf_path,
            max_pages_begin=settings.max_pages_begin,
            max_pages_end=settings.max_pages_end,
        )

        if not text:
            logger.warning(f"Texto não extraído para {pdf_path.name}.")
            control_rows.append({
                "timestamp_utc": utc_now_iso(),
                "arquivo": pdf_path.name,
                "arquivo_hash": file_hash,
                "status": "failed_no_text",
                "modelo_utilizado": "",
                "chunks_processados": 0,
                "cache_path": str(cache_path),
                "erro": extraction_meta.get("error", "texto_vazio"),
            })
            continue

        chunks = chunk_text(text, settings.max_chars_per_chunk, settings.chunk_overlap)
        chunk_payloads: list[dict[str, Any]] = []
        models_used: list[str] = []

        try:
            for chunk_number, chunk in enumerate(chunks, start=1):
                logger.info(f"Consultando LLM para chunk {chunk_number}/{len(chunks)} de {pdf_path.name}")
                prompt = build_extraction_prompt(chunk, settings.taxonomia_metodos)
                raw_payload, model_used = client.generate_json(prompt)
                normalized_payload = validate_and_normalize_payload(raw_payload)
                chunk_payloads.append(normalized_payload)
                models_used.append(model_used)
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
            processed_count += 1

            control_rows.append({
                "timestamp_utc": utc_now_iso(),
                "arquivo": pdf_path.name,
                "arquivo_hash": file_hash,
                "status": "success",
                "modelo_utilizado": record["metadata"]["model_used"],
                "chunks_processados": len(chunks),
                "cache_path": str(cache_path),
                "erro": "",
            })

        except Exception as exc:
            logger.exception(f"Falha ao extrair {pdf_path.name}: {exc}")
            control_rows.append({
                "timestamp_utc": utc_now_iso(),
                "arquivo": pdf_path.name,
                "arquivo_hash": file_hash,
                "status": "failed_llm",
                "modelo_utilizado": "",
                "chunks_processados": len(chunks),
                "cache_path": str(cache_path),
                "erro": str(exc),
            })

    control_csv = settings.extraction_control_dir / "controle_extracao.csv"
    append_rows_to_csv(control_csv, control_rows)
    logger.info(f"Extração concluída. Controle salvo em: {control_csv}")
    return {"processed": processed_count, "status": "ok", "control_csv": str(control_csv)}
