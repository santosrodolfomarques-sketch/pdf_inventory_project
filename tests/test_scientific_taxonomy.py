from __future__ import annotations

from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from src.core.config import Settings
from src.core.schemas import DictionaryItemModel, DictionaryModel
from src.normalization.normalizer import GeminiNormalizerClient, build_ai_dictionaries


@pytest.fixture
def temp_settings(tmp_path):
    settings = Settings()
    # Redireciona caminhos de normalização usando patch.object
    ai_norm_dir = tmp_path / "normalizacao_ia"
    ai_dict_dir = ai_norm_dir / "dicionarios_normalizacao"
    ai_dict_rev = ai_norm_dir / "revisar_ia"
    trans_uniq_dir = tmp_path / "valores_unicos"
    
    ai_norm_dir.mkdir(parents=True, exist_ok=True)
    ai_dict_dir.mkdir(parents=True, exist_ok=True)
    ai_dict_rev.mkdir(parents=True, exist_ok=True)
    trans_uniq_dir.mkdir(parents=True, exist_ok=True)
    
    with patch.object(Settings, "ai_normalization_dir", ai_norm_dir), \
         patch.object(Settings, "ai_dictionary_dir", ai_dict_dir), \
         patch.object(Settings, "ai_dictionary_review_dir", ai_dict_rev), \
         patch.object(Settings, "transformed_unique_dir", trans_uniq_dir):
        yield settings


@patch("src.normalization.normalizer.genai.Client")
def test_normalizer_client_prompts_steeepv_and_popper(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    
    # Prepara mock de retorno para generate_content
    mock_resp = MagicMock()
    mock_resp.text = '{"items": [{"valor_original": "Cenários de Clima", "valor_normalizado": "Mudanças Climáticas", "categoria": "Ecológico/Ambiental (E)", "subcategoria": "Clima", "confianca": "alta", "acao_recomendada": "aplicar automático", "justificativa": "Semântica próxima."}]}'
    mock_client.models.generate_content.return_value = mock_resp
    
    client = GeminiNormalizerClient(api_key="fake-key")
    
    # 1. Teste de Temas (STEEPV)
    res_temas = client.normalize_batch("temas", ["Cenários de Clima"])
    
    assert isinstance(res_temas, DictionaryModel)
    assert len(res_temas.items) == 1
    assert res_temas.items[0].categoria == "Ecológico/Ambiental (E)"
    
    # Verifica se os prompts continham STEEPV
    prompt_temas = mock_client.models.generate_content.call_args.kwargs["contents"]
    assert "STEEPV" in prompt_temas
    assert "Político/Governança (P)" in prompt_temas
    
    # 2. Teste de Métodos (Popper Foresight Diamond)
    # Prepara novo mock de retorno para métodos
    mock_resp.text = '{"items": [{"valor_original": "Oficinas Delphi", "valor_normalizado": "Delphi", "categoria": "Expertise (Foco Expert/Judgment)", "subcategoria": "Semi-Quantitativo", "confianca": "alta", "acao_recomendada": "aplicar automático", "justificativa": "Mesmo conceito."}]}'
    res_metodos = client.normalize_batch("metodos", ["Oficinas Delphi"])
    
    assert res_metodos.items[0].categoria == "Expertise (Foco Expert/Judgment)"
    assert res_metodos.items[0].subcategoria == "Semi-Quantitativo"
    
    # Verifica se os prompts continham Popper Foresight Diamond
    prompt_metodos = mock_client.models.generate_content.call_args.kwargs["contents"]
    assert "Popper Foresight Diamond" in prompt_metodos
    assert "Criatividade (Foco Speculative/Creativity)" in prompt_metodos


@patch("src.normalization.normalizer.genai.Client")
@patch("src.normalization.normalizer.MLNormalizer")
def test_build_ai_dictionaries_pipeline(mock_ml_cls, mock_client_cls, temp_settings):
    # 1. Mock do MLNormalizer para retornar vazio e forçar LLM
    mock_ml = MagicMock()
    mock_ml.suggest_normalization.return_value = None
    mock_ml_cls.return_value = mock_ml
    
    # 2. Mock do Gemini Client
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    
    mock_resp = MagicMock()
    mock_resp.text = '{"items": [{"valor_original": "termo_bruto", "valor_normalizado": "termo_limpo", "categoria": "Categoria X", "subcategoria": "Sub X", "confianca": "alta", "acao_recomendada": "aplicar automático", "justificativa": "ok"}]}'
    mock_client.models.generate_content.return_value = mock_resp
    
    # 3. Cria o arquivo de valores únicos que serve de input
    pd.DataFrame({"valor_original": ["termo_bruto"]}).to_csv(
        temp_settings.transformed_unique_dir / "valores_unicos_setor.csv",
        index=False
    )
    
    logger = MagicMock()
    
    # 4. Executa a construção do dicionário para o alvo 'setor'
    res = build_ai_dictionaries(temp_settings, logger, targets=["setor"])
    
    assert res["status"] == "ok"
    assert "setor" in res["targets"]
    assert res["targets"]["setor"]["termos_processados"] == 1
    assert res["targets"]["setor"]["processados_llm"] == 1
    
    # Verifica se o arquivo final foi criado e contém a estrutura correta
    out_csv = temp_settings.ai_dictionary_dir / "dicionario_setor.csv"
    assert out_csv.exists()
    
    df_result = pd.read_csv(out_csv)
    assert len(df_result) == 1
    assert df_result.loc[0, "valor_original"] == "termo_bruto"
    assert df_result.loc[0, "valor_normalizado"] == "termo_limpo"
    assert df_result.loc[0, "origem"] == "gemini_llm"
