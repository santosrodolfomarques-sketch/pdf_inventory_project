from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import numpy as np
import pandas as pd
from google import genai

from src.core.config import Settings
from src.extraction.extractor import extract_pdf_text_and_check


def calculate_document_embedding(pdf_path: Path, settings: Settings) -> list[float] | None:
    """Extrai texto representativo do PDF e gera seu embedding consolidado para busca de duplicidade."""
    try:
        # Extrai as primeiras 15 páginas para ter uma representação fiel do conteúdo sem estourar limites
        text, _ = extract_pdf_text_and_check(pdf_path, max_pages_begin=15, max_pages_end=0)
        if not text or len(text.strip()) < 20:
            return None
            
        client = genai.Client(api_key=settings.gemini_api_key, http_options={'timeout': 20.0})
        # Limita o texto para no máximo 30.000 caracteres
        truncated_text = text[:30000]
        response = client.models.embed_content(
            model="gemini-embedding-2",
            contents=truncated_text,
        )
        if response.embeddings and len(response.embeddings) > 0:
            return response.embeddings[0].values
    except Exception:
        pass
    return None


def get_document_embedding_by_name(pdf_name: str, settings: Settings) -> list[float] | None:
    """Localiza o arquivo JSON de extração cacheado associado a um PDF e extrai o vetor de embedding."""
    stem = Path(pdf_name).stem
    json_dir = Path(settings.extracted_json_dir)
    
    # Encontra arquivos de cache correspondentes (padrão: nome__hash.json)
    matched_files = list(json_dir.glob(f"{stem}__*.json"))
    if matched_files:
        try:
            with matched_files[0].open("r", encoding="utf-8") as f:
                data = json.load(f)
            # Retorna o vetor se existir
            emb = data.get("embedding")
            if emb and len(emb) > 0:
                return emb
        except Exception:
            pass
    return None


def find_semantic_duplicates(
    new_emb: list[float],
    df_consolidated: pd.DataFrame,
    settings: Settings,
    threshold: float = 0.85,
) -> dict[str, Any] | None:
    """Compara o embedding do novo PDF contra todos os documentos existentes na base consolidada.
    Retorna os detalhes do duplicado mais próximo se a similaridade de cosseno for superior ao limiar.
    """
    if not new_emb or df_consolidated is None or df_consolidated.empty:
        return None
        
    new_v = np.array(new_emb, dtype=np.float32)
    
    best_sim = -1.0
    best_row_idx = -1
    best_pdf_name = ""
    
    for idx, row in df_consolidated.iterrows():
        source_files_raw = row.get("source_files", "[]")
        try:
            # Converte a lista de arquivos de origem
            import ast
            s_files = ast.literal_eval(source_files_raw) if isinstance(source_files_raw, str) and source_files_raw.startswith("[") else source_files_raw
            if not isinstance(s_files, list):
                s_files = json.loads(source_files_raw) if isinstance(source_files_raw, str) else [source_files_raw]
        except Exception:
            s_files = [row.get("nome_documento")] if "nome_documento" in row else []
            
        if not s_files:
            continue
            
        # Carrega o embedding do primeiro arquivo de origem do documento consolidado
        app_emb = get_document_embedding_by_name(s_files[0], settings)
        if not app_emb:
            continue
            
        app_v = np.array(app_emb, dtype=np.float32)
        
        # Calcula similaridade de cosseno
        dot_prod = float(np.dot(new_v, app_v))
        norm_n = np.linalg.norm(new_v)
        norm_a = np.linalg.norm(app_v)
        
        sim = dot_prod / (norm_n * norm_a)
        if sim > best_sim:
            best_sim = sim
            best_row_idx = idx
            best_pdf_name = s_files[0]
            
    if best_sim >= threshold:
        return {
            "similaridade": round(best_sim * 100, 1),
            "nome_documento_duplicado": df_consolidated.loc[best_row_idx].get("nome_documento", "Sem título"),
            "arquivo_duplicado": best_pdf_name,
            "row_index": best_row_idx,
            "dados_consolidados": df_consolidated.loc[best_row_idx].to_dict()
        }
        
    return None
