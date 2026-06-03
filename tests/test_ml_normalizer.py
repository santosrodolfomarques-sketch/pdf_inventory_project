from __future__ import annotations

from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from src.core.config import Settings
from src.normalization.ml_normalizer import MLNormalizer


@pytest.fixture
def temp_settings(tmp_path):
    settings = Settings()
    # Redireciona os diretórios para uma pasta temporária do teste
    ai_norm_dir = tmp_path / "normalizacao_ia"
    ai_dict_dir = ai_norm_dir / "dicionarios_normalizacao"
    ai_dict_dir.mkdir(parents=True, exist_ok=True)
    
    # Mock das propriedades de diretório
    with patch.object(Settings, "ai_normalization_dir", ai_norm_dir), \
         patch.object(Settings, "ai_dictionary_dir", ai_dict_dir):
        yield settings


def test_ml_normalizer_exact_and_string_matching(temp_settings):
    # 1. Cria um dicionário CSV fake para testar
    dict_data = {
        "valor_original": ["Saneamento Básico", "Energia Solar", "Educação Superior"],
        "valor_normalizado": ["Saneamento", "Energia", "Educação"],
        "categoria": ["Infraestrutura", "Energia", "Social"],
        "subcategoria": ["Saneamento", "Recursos", "Educação"],
        "aplicar_automaticamente": [True, True, False]  # Educação Superior não deve ser aplicado automaticamente
    }
    df = pd.DataFrame(dict_data)
    df.to_csv(temp_settings.ai_dictionary_dir / "dicionario_setor.csv", index=False, encoding="utf-8-sig")
    
    # 2. Inicializa o MLNormalizer mockando o client do Gemini
    with patch("src.normalization.ml_normalizer.genai.Client") as mock_client:
        normalizer = MLNormalizer(settings=temp_settings)
        
        # Teste 1: Correspondência Exata (Case insensitive e sem acentos deve funcionar também)
        sug_exact = normalizer.suggest_normalization("setor", "Saneamento Básico")
        assert sug_exact is not None
        assert sug_exact["valor_normalizado"] == "Saneamento"
        assert sug_exact["categoria"] == "Infraestrutura"
        assert sug_exact["origem"] == "ml_exact"
        
        # Teste 2: Correspondência por String (difflib) - Pequeno erro de digitação
        sug_typo = normalizer.suggest_normalization("setor", "Saneamanto Basico")
        assert sug_typo is not None
        assert sug_typo["valor_normalizado"] == "Saneamento"
        assert sug_typo["origem"] == "ml_string"
        
        # Teste 3: Termo não aprovado automaticamente (deve retornar None ou não vir exato)
        sug_unapproved = normalizer.suggest_normalization("setor", "Educação Superior")
        assert sug_unapproved is None


def test_ml_normalizer_semantic_matching(temp_settings):
    # Cria o dicionário
    dict_data = {
        "valor_original": ["Transição Energética"],
        "valor_normalizado": ["Energia Limpa"],
        "categoria": ["Energia"],
        "subcategoria": ["Transição"],
        "aplicar_automaticamente": [True]
    }
    pd.DataFrame(dict_data).to_csv(temp_settings.ai_dictionary_dir / "dicionario_setor.csv", index=False, encoding="utf-8-sig")
    
    # Mock do Gemini Client e do método embed_content
    with patch("src.normalization.ml_normalizer.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        
        # Embedding do termo cadastrado no dicionário ("Transição Energética")
        mock_emb_registered = MagicMock()
        mock_emb_registered.values = [0.1] * 768
        
        # Embedding do termo de teste ("Descarbonização")
        mock_emb_query = MagicMock()
        mock_emb_query.values = [0.102] * 768  # Vetor muito similar ao anterior
        
        # Retorna embeddings mockados em ordem
        mock_resp = MagicMock()
        mock_resp.embeddings = [mock_emb_registered, mock_emb_query]
        mock_client.models.embed_content.return_value = mock_resp
        
        # Inicializa o normalizador (que vai gerar o cache durante o aquecimento)
        normalizer = MLNormalizer(settings=temp_settings)
        
        # Agora mockamos a chamada de embedding única para a query
        mock_query_resp = MagicMock()
        mock_query_resp.embeddings = [mock_emb_query]
        mock_client.models.embed_content.return_value = mock_query_resp
        
        sug = normalizer.suggest_normalization("setor", "Descarbonização")
        assert sug is not None
        assert sug["valor_normalizado"] == "Energia Limpa"
        assert sug["origem"] == "ml_semantic"
