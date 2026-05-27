from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pandas as pd
from google import genai
from google.genai import types

from src.core.config import Settings
from src.core.schemas import DictionaryModel
from src.transformation.cleansing import remove_accents


class GeminiNormalizerClient:
    """Cliente Gemini modernizado para criar dicionários estruturados de normalização em lote."""

    def __init__(
        self,
        api_key: str,
        model_lite: str = "gemini-2.5-flash-lite",
        model_flash: str = "gemini-2.5-flash",
        model_pro: str = "gemini-2.5-pro",
        max_retries: int = 3,
        logger: Any | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY não configurada. Verifique seu arquivo .env.")
        self.client = genai.Client(api_key=api_key)
        self.model_lite = model_lite
        self.model_flash = model_flash
        self.model_pro = model_pro
        self.max_retries = max_retries
        self.logger = logger

    def _log(self, message: str) -> None:
        if self.logger:
            self.logger.info(message)

    def normalize_batch(self, target_name: str, values: list[str]) -> DictionaryModel:
        """Gera propostas de normalização para um lote de valores brutos usando Structured Outputs."""
        if not values:
            return DictionaryModel(items=[])

        prompt = f"""
Você é um curador de dados analíticos especialista em higienização, taxonomia e preparação de bases de BI.
Sua missão é ler a lista de valores brutos extraídos de documentos e sugerir uma tabela de normalização estruturada.

CAMPO ALVO: {target_name}

DIRETRIZES:
1. Agrupe sinônimos óbvios, variações de escrita, caixa alta/baixa, erros de digitação e plurais sob um único termo normalizado.
2. Seja conservador: não mescle conceitos distintos. Se houver dúvida, mantenha o termo original ou sugira revisão manual.
3. Para cada item, preencha:
   - valor_original: exatamente igual ao enviado.
   - valor_normalizado: o termo padronizado (ou null se deve manter o original).
   - categoria: categoria ampla (ex.: setor energético, instituição pública, tema ambiental, etc.).
   - confianca: 'alta' (certeza da equivalência), 'media' ou 'baixa'.
   - acao_recomendada: 'aplicar automático' (se a confiança for alta), 'revisar manualmente' (se for ambíguo) ou 'manter original' (se o termo já estiver perfeito).
   - justificativa: uma frase explicativa curta.

VALORES BRUTOS A ANALISAR:
{json.dumps(values, ensure_ascii=False, indent=2)}
        """.strip()

        # Cadeia de fallback progressiva
        model_chain = [self.model_lite, self.model_flash, self.model_pro]
        last_error = None
        
        for attempt in range(self.max_retries):
            idx = min(attempt, len(model_chain) - 1)
            model_name = model_chain[idx]
            try:
                if attempt > 0:
                    self._log(f"Fallback normalizador acionado: mudando para {model_name} na tentativa {attempt + 1}")

                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=DictionaryModel,
                        temperature=0.1,
                    ),
                )
                parsed = DictionaryModel.model_validate_json(response.text)
                return parsed

            except Exception as exc:
                last_error = exc
                self._log(f"Falha ao normalizar lote de {target_name} ({model_name}) | tentativa {attempt+1}: {exc}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)

        raise RuntimeError(f"Erro definitivo ao normalizar {target_name}: {last_error}")


import json


def _chunk_list(lst: list[Any], n: int) -> list[list[Any]]:
    return [lst[i:i + n] for i in range(0, len(lst), n)]


def build_ai_dictionaries(
    settings: Settings,
    logger: Any,
    targets: list[str] | None = None,
    only_new_values: bool = False,
) -> dict[str, Any]:
    """Lê os valores únicos salvos pela transformação e propõe dicionários estruturados via IA."""
    targets = targets or ["setor", "tipo_documento", "abrangencia_territorial", "tipo_estudo_futuro", "instituicao_responsavel"]

    settings.ai_dictionary_dir.mkdir(parents=True, exist_ok=True)
    settings.ai_dictionary_review_dir.mkdir(parents=True, exist_ok=True)

    client = GeminiNormalizerClient(
        api_key=settings.gemini_api_key,
        model_lite=settings.model_lite,
        model_flash=settings.model_flash,
        model_pro=settings.model_pro,
        max_retries=settings.max_retries,
        logger=logger,
    )

    summary: dict[str, Any] = {"status": "ok", "targets": {}}

    for target in targets:
        unique_file = settings.transformed_unique_dir / f"valores_unicos_{target}.csv"
        if not unique_file.exists():
            logger.warning(f"Arquivo de valores únicos não encontrado: {unique_file.name}")
            continue

        df_unique = pd.read_csv(unique_file)
        if df_unique.empty or "valor_original" not in df_unique.columns:
            logger.info(f"Sem valores para normalizar no arquivo: {unique_file.name}")
            continue

        valores_brutos = sorted(list(df_unique["valor_original"].dropna().astype(str).unique()))
        out_path = settings.ai_dictionary_dir / f"dicionario_{target}.csv"

        # Se apenas novos valores, remove os que já estão no dicionário
        if only_new_values and out_path.exists():
            df_old = pd.read_csv(out_path)
            if not df_old.empty and "valor_original" in df_old.columns:
                existing_keys = set(df_old["valor_original"].astype(str).tolist())
                valores_brutos = [v for v in valores_brutos if v not in existing_keys]

        if not valores_brutos:
            logger.info(f"Alvo {target}: nenhum valor novo a normalizar.")
            continue

        # Processamento em lotes (Batching)
        lotes = _chunk_list(valores_brutos, settings.ai_dictionary_batch_size)
        items_sugeridos = []

        for idx, lote in enumerate(lotes, start=1):
            logger.info(f"Normalizando {target} | lote {idx}/{len(lotes)} ({len(lote)} termos)...")
            try:
                dict_model = client.normalize_batch(target, lote)
                for item in dict_model.items:
                    row = item.model_dump()
                    row["valor_original_limpo"] = remove_accents(row["valor_original"]).lower()
                    row["aplicar_automaticamente"] = row["acao_recomendada"] == "aplicar automático"
                    items_sugeridos.append(row)
                time.sleep(settings.pause_between_calls)
            except Exception as exc:
                logger.error(f"Erro ao normalizar lote {idx} de {target}: {exc}")

        if not items_sugeridos:
            continue

        df_result = pd.DataFrame(items_sugeridos)

        # Se apenas novos valores, mescla com o antigo
        if only_new_values and out_path.exists():
            df_old = pd.read_csv(out_path)
            df_result = pd.concat([df_old, df_result], ignore_index=True).drop_duplicates(
                subset=["valor_original"], keep="last"
            )

        # Salva o dicionário final
        df_result.to_csv(out_path, index=False, encoding="utf-8-sig")

        # Cria uma visualização rápida do que precisa de revisão manual
        df_revisar = df_result[~df_result["aplicar_automaticamente"]].copy()
        df_revisar.to_csv(settings.ai_dictionary_review_dir / f"revisar_{target}.csv", index=False, encoding="utf-8-sig")

        summary["targets"][target] = {
            "termos_processados": len(valores_brutos),
            "revisoes_pendentes": len(df_revisar),
            "dicionario_path": str(out_path),
        }

    return summary
