from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from src.core.config import Settings
from src.core.schemas import ExtractionModel
from src.extraction.extractor import GeminiExtractorClient, extract_pdf_text_and_check
from src.extraction.cache_manager import build_cache_path, load_cached_extraction, save_cached_extraction
from src.shared.utils import append_rows_to_csv, file_sha256, utc_now_iso, write_json, read_json

FAILED_STATUSES = {
    "failed_no_text",
    "failed_llm",
    "failed_api",
    "failed_json",
    "failed_unexpected",
}


def _control_row(
    *,
    pdf_path: Path,
    file_hash: str,
    status: str,
    cache_path: Path,
    model_used: str = "",
    needs_ocr: bool = False,
    error: str = "",
) -> dict[str, Any]:
    return {
        "timestamp_utc": utc_now_iso(),
        "arquivo": pdf_path.name,
        "arquivo_hash": file_hash,
        "status": status,
        "modelo_utilizado": model_used,
        "needs_ocr": str(needs_ocr),
        "cache_path": str(cache_path),
        "erro": error,
    }


def chunk_text(text: str, max_chars: int = 120000, overlap: int = 5000) -> list[str]:
    """Divide um texto longo em blocos de tamanho controlado com sobreposição."""
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunks.append(text[start:end])
        start += max_chars - overlap
    return chunks


def merge_extraction_models(models: list[ExtractionModel]) -> ExtractionModel:
    """Consolida e unifica múltiplos resultados de blocos usando Pydantic."""
    if not models:
        return ExtractionModel()

    def coalesce(*values: Any) -> Any:
        for val in values:
            if val is not None and val != "" and val != []:
                return val
        return None

    def merge_lists(*lists: list[str]) -> list[str]:
        seen = set()
        merged = []
        for lst in lists:
            for item in lst:
                cleaned = str(item).strip()
                if cleaned and cleaned.lower() not in seen:
                    seen.add(cleaned.lower())
                    merged.append(cleaned)
        return sorted(merged)

    merged = ExtractionModel()
    merged.nome_documento = coalesce(*(m.nome_documento for m in models))
    merged.tipo_documento = coalesce(*(m.tipo_documento for m in models))
    merged.ano_publicacao = coalesce(*(m.ano_publicacao for m in models))
    merged.horizonte_temporal = coalesce(*(m.horizonte_temporal for m in models))
    merged.abrangencia_territorial = coalesce(*(m.abrangencia_territorial for m in models))
    merged.setor = coalesce(*(m.setor for m in models))
    merged.tipo_estudo_futuro = coalesce(*(m.tipo_estudo_futuro for m in models))
    merged.instituicao_responsavel = coalesce(*(m.instituicao_responsavel for m in models))

    bool_values = [m.aplicou_estudo_futuro for m in models if m.aplicou_estudo_futuro is not None]
    merged.aplicou_estudo_futuro = True in bool_values if bool_values else None

    merged.temas = merge_lists(*(m.temas for m in models))
    merged.metodos_estudo_futuro = merge_lists(*(m.metodos_estudo_futuro for m in models))
    merged.referencias = merge_lists(*(m.referencias for m in models))
    merged.condicionantes_estudo_futuro = merge_lists(*(m.condicionantes_estudo_futuro for m in models))
    merged.instituicoes_apoio = merge_lists(*(m.instituicoes_apoio for m in models))

    return merged


def run_extraction(
    settings: Settings,
    logger: Any,
    force_reprocess: bool = False,
    only_failed: bool = False,
) -> dict[str, Any]:
    """Orquestra o lote de extração usando leitor adaptativo e controle rígido de duplicados."""
    pdf_files = sorted(Path(settings.raw_pdf_dir).glob("*.pdf"))
    control_csv = settings.extraction_control_dir / "controle_extracao.csv"

    if not pdf_files:
        logger.info("Nenhum PDF encontrado na pasta bruta.")
        return {"processed": 0, "status": "empty"}

    client = GeminiExtractorClient(
        api_key=settings.gemini_api_key,
        model_lite=settings.model_lite,
        model_flash=settings.model_flash,
        model_pro=settings.model_pro,
        max_retries=settings.max_retries,
        logger=logger,
    )

    processed_count = 0
    failed_count = 0
    skipped_count = 0
    control_rows: list[dict[str, Any]] = []

    # Dicionário na memória para rastrear hashes já processados neste lote
    processed_hashes: dict[str, Path] = {}

    for index, pdf_path in enumerate(pdf_files, start=1):
        logger.info(f"[{index}/{len(pdf_files)}] Processando PDF: {pdf_path.name}")
        try:
            file_hash = file_sha256(pdf_path)
        except Exception as exc:
            logger.exception(f"Erro ao gerar hash do PDF: {exc}")
            failed_count += 1
            continue

        cache_path = build_cache_path(settings.extracted_json_dir, pdf_path.stem, file_hash)

        # 1. DEDUPLICAÇÃO REAL POR HASH (Novidade sugerida pelo usuário!)
        if file_hash in processed_hashes:
            dup_origem = processed_hashes[file_hash]
            logger.info(f"Arquivo idêntico detectado por hash! Duplicado de: {dup_origem.name}. Copiando cache e pulando API.")
            
            # Copia o cache já gerado do primeiro para o segundo
            orig_cache_path = build_cache_path(settings.extracted_json_dir, dup_origem.stem, file_hash)
            if orig_cache_path.exists():
                try:
                    write_json(cache_path, read_json(orig_cache_path))
                except Exception:
                    pass

            control_rows.append(_control_row(
                pdf_path=pdf_path,
                file_hash=file_hash,
                status="skipped_duplicate",
                cache_path=cache_path,
                error=f"Conteúdo duplicado idêntico ao arquivo {dup_origem.name}",
            ))
            skipped_count += 1
            processed_count += 1
            append_rows_to_csv(control_csv, control_rows)
            control_rows.clear()
            continue

        # Registra o hash na memória
        processed_hashes[file_hash] = pdf_path

        # Checagem de cache local
        cached = None if force_reprocess else load_cached_extraction(cache_path)
        if cached:
            logger.info("Registro encontrado no cache de extração. Pulando chamada de IA.")
            control_rows.append(_control_row(
                pdf_path=pdf_path,
                file_hash=file_hash,
                status="cache_hit",
                cache_path=cache_path,
                model_used=cached.get("metadata", {}).get("model_used", ""),
            ))
            processed_count += 1
            continue

        # ============================================================
        # 2. LEITURA ADAPTATIVA EM DUAS ETAPAS (Novidade sugerida pelo usuário!)
        # ============================================================
        
        # ETAPA 1: Amostragem Rápida e Barata (Apenas Capa e Final - 3 págs início, 2 págs fim)
        logger.info("Etapa 1: Tentando amostragem adaptativa ultra barata (3 págs início, 2 págs fim)...")
        text, extraction_meta = extract_pdf_text_and_check(
            pdf_path,
            max_pages_begin=3,
            max_pages_end=2,
        )

        if extraction_meta.get("error") or extraction_meta.get("needs_ocr") or not text:
            # Se deu erro físico ou precisa de OCR, pula direto
            logger.warning(f"Erro ou necessidade de OCR detectada. Interrompendo amostragem adaptativa.")
            control_rows.append(_control_row(
                pdf_path=pdf_path,
                file_hash=file_hash,
                status="failed_no_text" if extraction_meta.get("needs_ocr") else "failed_unexpected",
                cache_path=cache_path,
                needs_ocr=extraction_meta.get("needs_ocr", False),
                error=extraction_meta.get("error") or "empty_or_ocr",
            ))
            failed_count += 1
            append_rows_to_csv(control_csv, control_rows)
            control_rows.clear()
            continue

        # Faz extração rápida na Etapa 1
        logger.info("Chamando Gemini para extração estruturada de Etapa 1...")
        try:
            model_payload, model_name = client.generate_metadata(text)
            
            # Critério de Decisão Adaptativa: se campos chaves vieram nulos, escalamos
            needs_scale_up = any([
                not model_payload.nome_documento,
                model_payload.ano_publicacao is None,
                not model_payload.setor,
                not model_payload.tipo_documento,
            ])
            
            if needs_scale_up:
                # ETAPA 2: Escala a leitura se faltaram metadados essenciais
                logger.info("Metadados essenciais ausentes na Etapa 1. Escalando para Etapa 2 (maior escopo e contexto)...")
                text, extraction_meta = extract_pdf_text_and_check(
                    pdf_path,
                    max_pages_begin=settings.max_pages_begin,
                    max_pages_end=settings.max_pages_end,
                )
                
                # Executa extração completa de Etapa 2
                chunks = chunk_text(text, settings.max_chars_per_chunk, settings.chunk_overlap)
                chunk_models = []
                models_used = []
                
                for c_idx, chunk in enumerate(chunks, start=1):
                    logger.info(f"Chamando Gemini (Etapa 2) para o bloco {c_idx}/{len(chunks)}...")
                    payload, m_used = client.generate_metadata(chunk)
                    chunk_models.append(payload)
                    models_used.append(m_used)
                    time.sleep(settings.pause_between_calls)
                
                final_model = merge_extraction_models(chunk_models)
                model_name = " | ".join(sorted(set(models_used)))
            else:
                logger.info("Extração da Etapa 1 concluída com absoluto sucesso e economia de tokens!")
                final_model = model_payload
                chunks = ["bloco_unico_etapa1"]

            # GERAÇÃO DE EMBEDDINGS
            logger.info("Gerando representação de embedding vetorial do documento...")
            embedding_vector = client.generate_embeddings(text[:25000])

            # Prepara registro estruturado para o Cache JSON
            record = {
                "metadata": {
                    "source_file_name": pdf_path.name,
                    "source_file_path": str(pdf_path),
                    "source_file_hash": file_hash,
                    "processed_at_utc": utc_now_iso(),
                    "model_used": model_name,
                    "chunk_count": len(chunks),
                    "extraction_details": extraction_meta,
                },
                "payload": final_model.model_dump(),
                "embedding": embedding_vector,
            }

            save_cached_extraction(cache_path, record)
            processed_count += 1

            control_rows.append(_control_row(
                pdf_path=pdf_path,
                file_hash=file_hash,
                status="success",
                cache_path=cache_path,
                model_used=record["metadata"]["model_used"],
            ))

        except Exception as exc:
            logger.exception(f"Falha ao extrair dados na rotina adaptativa: {exc}")
            failed_count += 1
            control_rows.append(_control_row(
                pdf_path=pdf_path,
                file_hash=file_hash,
                status="failed_llm",
                cache_path=cache_path,
                error=str(exc),
            ))

        append_rows_to_csv(control_csv, control_rows)
        control_rows.clear()

    return {
        "processed": processed_count,
        "failed": failed_count,
        "skipped_duplicates": skipped_count,
        "status": "ok" if failed_count == 0 else "warning",
    }
