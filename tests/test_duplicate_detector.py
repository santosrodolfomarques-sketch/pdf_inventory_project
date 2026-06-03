from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pandas as pd
import pytest

from src.core.config import Settings
from src.extraction.detector import (
    calculate_document_embedding,
    find_semantic_duplicates,
    get_document_embedding_by_name,
)


@pytest.fixture
def temp_settings(tmp_path):
    settings = Settings()
    # Redireciona caminhos de diretório para teste isolado usando patch.object nas propriedades
    ext_dir = tmp_path / "extraidos"
    raw_dir = tmp_path / "brutos"
    ext_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    with patch.object(Settings, "extracted_json_dir", ext_dir), \
         patch.object(Settings, "raw_pdf_dir", raw_dir):
        yield settings


def test_get_document_embedding_by_name(temp_settings):
    # 1. Cria arquivo de cache falso no formato nome__hash.json
    cache_data = {
        "status": "success",
        "embedding": [0.1, 0.2, 0.3],
        "metadata": {"source_file_name": "teste_doc.pdf"}
    }
    
    cache_file = temp_settings.extracted_json_dir / "teste_doc__hash123.json"
    with cache_file.open("w", encoding="utf-8") as f:
        json.dump(cache_data, f)
        
    # 2. Testa a recuperação por nome
    emb = get_document_embedding_by_name("teste_doc.pdf", temp_settings)
    assert emb == [0.1, 0.2, 0.3]
    
    # 3. Testa com arquivo inexistente
    emb_missing = get_document_embedding_by_name("inexistente.pdf", temp_settings)
    assert emb_missing is None


@patch("src.extraction.detector.extract_pdf_text_and_check")
@patch("src.extraction.detector.genai.Client")
def test_calculate_document_embedding(mock_client_cls, mock_extract, temp_settings):
    # 1. Configura mocks
    mock_extract.return_value = ("Texto de teste para o PDF", {"paginas": 1})
    
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    
    mock_emb = MagicMock()
    mock_emb.values = [0.5, 0.6, 0.7]
    mock_resp = MagicMock()
    mock_resp.embeddings = [mock_emb]
    mock_client.models.embed_content.return_value = mock_resp
    
    # 2. Executa cálculo do embedding
    pdf_path = temp_settings.raw_pdf_dir / "teste_doc.pdf"
    pdf_path.touch()
    
    emb = calculate_document_embedding(pdf_path, temp_settings)
    
    assert emb == [0.5, 0.6, 0.7]
    mock_extract.assert_called_once_with(pdf_path, max_pages_begin=15, max_pages_end=0)
    mock_client.models.embed_content.assert_called_once()
    args, kwargs = mock_client.models.embed_content.call_args
    assert kwargs["model"] == "gemini-embedding-2"
    assert kwargs["contents"] == "Texto de teste para o PDF"


@patch("src.extraction.detector.get_document_embedding_by_name")
def test_find_semantic_duplicates(mock_get_emb, temp_settings):
    # 1. Configura dataframe consolidado simulado
    df_consolidated = pd.DataFrame([
        {
            "nome_documento": "Documento A",
            "source_files": "['doc_a.pdf']"
        },
        {
            "nome_documento": "Documento B",
            "source_files": "['doc_b.pdf']"
        }
    ])
    
    # 2. Configura mock de embeddings cadastrados na base
    # Embedding do Documento A: [1.0, 0.0, 0.0]
    # Embedding do Documento B: [0.0, 1.0, 0.0]
    def mock_emb_side_effect(pdf_name, settings):
        if pdf_name == "doc_a.pdf":
            return [1.0, 0.0, 0.0]
        if pdf_name == "doc_b.pdf":
            return [0.0, 1.0, 0.0]
        return None
    mock_get_emb.side_effect = mock_emb_side_effect
    
    # Caso 1: Embedding novo é [0.99, 0.0, 0.0] -> Deve bater com Documento A (cosseno ~ 0.99)
    new_emb_close = [0.99, 0.0, 0.0]
    dup = find_semantic_duplicates(new_emb_close, df_consolidated, temp_settings, threshold=0.85)
    
    assert dup is not None
    assert dup["nome_documento_duplicado"] == "Documento A"
    assert dup["arquivo_duplicado"] == "doc_a.pdf"
    assert dup["similaridade"] >= 99.0
    
    # Caso 2: Embedding novo é [0.0, 0.0, 1.0] -> Nenhuma similaridade ultrapassa 0.85
    new_emb_far = [0.0, 0.0, 1.0]
    dup_none = find_semantic_duplicates(new_emb_far, df_consolidated, temp_settings, threshold=0.85)
    assert dup_none is None
