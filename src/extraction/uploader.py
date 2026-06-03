from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any

from src.core.config import Settings
from src.core.schemas import ExtractionModel
from src.extraction.extractor import GeminiExtractorClient, extract_pdf_text_and_check
from src.extraction.pipeline import chunk_text, merge_extraction_models
from src.shared.utils import file_sha256, utc_now_iso, write_json, read_json


def extract_single_pdf(
    pdf_path: Path,
    settings: Settings,
    logger: Any,
    force_reprocess: bool = False,
) -> dict[str, Any]:
    """Extrai metadados estruturados e embeddings de um único PDF específico sem gravar no diretório de cache oficial."""
    file_hash = file_sha256(pdf_path)
    
    # Prepara o extrator Gemini
    client = GeminiExtractorClient(
        api_key=settings.gemini_api_key,
        model_lite=settings.model_lite,
        model_flash=settings.model_flash,
        model_pro=settings.model_pro,
        max_retries=settings.max_retries,
        logger=logger,
    )
    
    # Executa a leitura adaptativa de 2 etapas
    logger.info(f"Iniciando extração para arquivo único: {pdf_path.name}")
    
    # Etapa 1: Amostragem Rápida
    text, extraction_meta = extract_pdf_text_and_check(
        pdf_path,
        max_pages_begin=3,
        max_pages_end=2,
    )
    
    if extraction_meta.get("error") or extraction_meta.get("needs_ocr") or not text:
        return {
            "status": "failed",
            "error": extraction_meta.get("error") or "Falta de texto ou necessidade de OCR",
            "file_hash": file_hash,
            "file_name": pdf_path.name,
            "needs_ocr": extraction_meta.get("needs_ocr", False),
        }
        
    try:
        model_payload, model_name = client.generate_metadata(text)
        
        needs_scale_up = any([
            not model_payload.nome_documento,
            model_payload.ano_publicacao is None,
            not model_payload.setor,
            not model_payload.tipo_documento,
        ])
        
        if needs_scale_up:
            logger.info("Escalando leitura para a Etapa 2...")
            text, extraction_meta = extract_pdf_text_and_check(
                pdf_path,
                max_pages_begin=settings.max_pages_begin,
                max_pages_end=settings.max_pages_end,
            )
            
            chunks = chunk_text(text, settings.max_chars_per_chunk, settings.chunk_overlap)
            chunk_models = []
            models_used = []
            
            for chunk in chunks:
                payload, m_used = client.generate_metadata(chunk)
                chunk_models.append(payload)
                models_used.append(m_used)
                time.sleep(settings.pause_between_calls)
                
            final_model = merge_extraction_models(chunk_models)
            model_name = " | ".join(sorted(set(models_used)))
        else:
            final_model = model_payload
            
        logger.info("Gerando embedding do documento...")
        embedding_vector = client.generate_embeddings(text[:25000])
        
        record = {
            "status": "success",
            "metadata": {
                "source_file_name": pdf_path.name,
                "source_file_path": str(pdf_path),
                "source_file_hash": file_hash,
                "processed_at_utc": utc_now_iso(),
                "model_used": model_name,
                "extraction_details": extraction_meta,
            },
            "payload": final_model.model_dump(),
            "embedding": embedding_vector,
        }
        return record
        
    except Exception as e:
        logger.error(f"Erro na extração adaptativa: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "file_hash": file_hash,
            "file_name": pdf_path.name,
        }


def commit_pdf_to_base(
    temp_pdf_path: Path,
    extraction_record: dict[str, Any],
    settings: Settings,
    logger: Any,
) -> Path:
    """Move o PDF físico para a pasta oficial de PDFs brutos e grava seu cache JSON.
    Retorna o caminho final do arquivo de cache.
    """
    file_name = extraction_record["metadata"]["source_file_name"]
    file_hash = extraction_record["metadata"]["source_file_hash"]
    
    # Destinos oficiais
    final_pdf_path = settings.raw_pdf_dir / file_name
    from src.extraction.cache_manager import build_cache_path
    final_cache_path = build_cache_path(settings.extracted_json_dir, Path(file_name).stem, file_hash)
    
    # Garante que os diretórios existam
    settings.raw_pdf_dir.mkdir(parents=True, exist_ok=True)
    settings.extracted_json_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Copia o PDF físico
    if temp_pdf_path != final_pdf_path:
        shutil.copy2(temp_pdf_path, final_pdf_path)
        logger.info(f"Copiado PDF para pasta definitiva: {final_pdf_path.name}")
        
    # 2. Grava o cache JSON
    # Atualiza o caminho físico no metadado
    extraction_record["metadata"]["source_file_path"] = str(final_pdf_path)
    write_json(final_cache_path, extraction_record)
    logger.info(f"Gravado cache JSON oficial em: {final_cache_path.name}")
    
    return final_cache_path
