from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from src.core.config import Settings
from src.core.schemas import ExtractionModel
from src.extraction.extractor import GeminiExtractorClient, extract_pdf_text_and_check
from src.shared.utils import file_sha256, utc_now_iso, write_json


def extract_single_pdf(
    pdf_path: Path,
    settings: Settings,
    logger: Any,
    force_reprocess: bool = False,
) -> dict[str, Any]:
    """Extrai metadados estruturados de um PDF carregando-o para a Files API do Gemini
    e garante sua remoção após a conclusão para privacidade dos dados.
    """
    file_hash = file_sha256(pdf_path)
    logger.info(f"Iniciando extração via Files API para: {pdf_path.name}")
    
    # 1. Prepara os clientes
    client_gen = genai.Client(api_key=settings.gemini_api_key)
    client_extractor = GeminiExtractorClient(
        api_key=settings.gemini_api_key,
        model_lite=settings.model_lite,
        model_flash=settings.model_flash,
        model_pro=settings.model_pro,
        max_retries=settings.max_retries,
        logger=logger,
    )
    
    # 2. Faz o upload do PDF físico para a Files API do Gemini
    logger.info(f"Fazendo upload do arquivo para o servidor Gemini...")
    uploaded_file = client_gen.files.upload(file=pdf_path)
    logger.info(f"Upload concluído. Identificador na nuvem: {uploaded_file.name}")
    
    try:
        # Define os modelos para a cadeia de fallback
        model_chain = [settings.model_flash, settings.model_pro]
        final_payload = None
        model_used = ""
        last_error = None
        
        # Executa a extração usando a capacidade multimodal nativa do Gemini
        for attempt, model_name in enumerate(model_chain, start=1):
            logger.info(f"Tentativa {attempt} usando o modelo: {model_name}...")
            try:
                response = client_gen.models.generate_content(
                    model=model_name,
                    contents=[
                        "Você é um analista especialista em curadoria de documentos técnicos.\n"
                        "Sua missão é extrair de forma rigorosa os metadados do documento PDF anexo.",
                        uploaded_file
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ExtractionModel,
                        temperature=0.1,
                    )
                )
                final_payload = ExtractionModel.model_validate_json(response.text)
                model_used = model_name
                logger.info(f"Extração concluída com sucesso usando {model_name}.")
                break
            except Exception as e:
                last_error = e
                logger.warning(f"Falha na extração com {model_name}: {e}")
                if attempt < len(model_chain):
                    time.sleep(2)
                    
        if final_payload is None:
            raise RuntimeError(f"Erro definitivo ao extrair metadados via Files API: {last_error}")
            
        # 3. Extração local de texto parcial apenas para geração do vetor de Embedding
        logger.info("Extraindo texto parcial localmente para geração de embeddings...")
        text_for_embedding, extraction_meta = extract_pdf_text_and_check(
            pdf_path,
            max_pages_begin=15,
            max_pages_end=0,
        )
        
        logger.info("Gerando representação de embedding com o modelo gemini-embedding-2...")
        embedding_vector = client_extractor.generate_embeddings(text_for_embedding[:25000])
        
        record = {
            "status": "success",
            "metadata": {
                "source_file_name": pdf_path.name,
                "source_file_path": str(pdf_path),
                "source_file_hash": file_hash,
                "processed_at_utc": utc_now_iso(),
                "model_used": model_used,
                "extraction_details": extraction_meta,
            },
            "payload": final_payload.model_dump(),
            "embedding": embedding_vector,
        }
        return record
        
    except Exception as e:
        logger.error(f"Falha ao processar arquivo {pdf_path.name}: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "file_hash": file_hash,
            "file_name": pdf_path.name,
        }
        
    finally:
        # 4. Exclusão segura e explícita do arquivo dos servidores do Gemini
        logger.info(f"Removendo arquivo do servidor Gemini de forma segura: {uploaded_file.name}")
        try:
            client_gen.files.delete(name=uploaded_file.name)
            logger.info("Arquivo removido da nuvem do Gemini com sucesso.")
        except Exception as delete_error:
            logger.error(f"Erro ao deletar arquivo temporário da nuvem: {delete_error}")


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
