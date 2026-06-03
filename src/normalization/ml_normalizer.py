from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import difflib

import numpy as np
import pandas as pd
from google import genai

from src.core.config import Settings
from src.transformation.cleansing import remove_accents


class MLNormalizer:
    """Normalizador híbrido que utiliza regras exatas, distância de edição (difflib)
    e busca por similaridade semântica (Gemini Embeddings) para aprender com as curadorias do usuário.
    """

    def __init__(
        self,
        settings: Settings,
        logger: Any | None = None,
        embedding_model: str = "gemini-embedding-2",
        min_semantic_similarity: float = 0.88,
        min_string_similarity: float = 0.93,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.embedding_model = embedding_model
        self.min_semantic_similarity = min_semantic_similarity
        self.min_string_similarity = min_string_similarity
        
        # Inicializa cliente Gemini
        self.client = genai.Client(api_key=settings.gemini_api_key)
        
        # Caminho para o cache de embeddings persistente
        self.cache_path = settings.ai_normalization_dir / "embeddings_approved_cache.json"
        self.embeddings_cache: dict[str, list[float]] = {}
        self._load_embeddings_cache()
        
        # Dicionários em memória dos mapeamentos aprovados
        # Formato: {target_name: {valor_original_limpo: (valor_normalizado, categoria, subcategoria)}}
        self.approved_mappings: dict[str, dict[str, tuple[str, str, str]]] = {}
        # Lista dos valores originais originais para busca de similaridade
        # Formato: {target_name: [valor_original_real]}
        self.approved_original_values: dict[str, list[str]] = {}
        
        self.load_approved_mappings()

    def _log(self, message: str) -> None:
        if self.logger:
            self.logger.info(message)

    def _load_embeddings_cache(self) -> None:
        """Carrega cache de embeddings de arquivo local."""
        if self.cache_path.exists():
            try:
                with self.cache_path.open("r", encoding="utf-8") as f:
                    self.embeddings_cache = json.load(f)
            except Exception as e:
                self._log(f"Erro ao carregar cache de embeddings: {e}")

    def _save_embeddings_cache(self) -> None:
        """Salva cache de embeddings no arquivo local."""
        self.settings.ai_normalization_dir.mkdir(parents=True, exist_ok=True)
        try:
            with self.cache_path.open("w", encoding="utf-8") as f:
                json.dump(self.embeddings_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._log(f"Erro ao salvar cache de embeddings: {e}")

    def load_approved_mappings(self) -> None:
        """Carrega mapeamentos aprovados dos dicionários CSV em disco."""
        targets = ["setor", "tipo_documento", "abrangencia_territorial", "tipo_estudo_futuro", "instituicao_responsavel", "temas", "metodos", "condicionantes"]
        
        for target in targets:
            self.approved_mappings[target] = {}
            self.approved_original_values[target] = []
            
            dict_path = self.settings.ai_dictionary_dir / f"dicionario_{target}.csv"
            if not dict_path.exists():
                continue
                
            try:
                df = pd.read_csv(dict_path)
                if df.empty:
                    continue
                
                # Consideramos aprovados os termos que o usuário ou sistema marcaram para aplicar_automaticamente
                df_approved = df[df["aplicar_automaticamente"].astype(str).str.lower().isin(["true", "1", "sim", "yes"])]
                
                for _, row in df_approved.iterrows():
                    orig = str(row.get("valor_original", "")).strip()
                    norm = row.get("valor_normalizado")
                    cat = row.get("categoria", "Outros / Não Classificado")
                    subcat = row.get("subcategoria", "")
                    
                    if orig and pd.notna(norm):
                        key = remove_accents(orig).lower()
                        self.approved_mappings[target][key] = (str(norm).strip(), str(cat).strip(), str(subcat).strip())
                        self.approved_original_values[target].append(orig)
            except Exception as e:
                self._log(f"Erro ao carregar dicionário de {target} no MLNormalizer: {e}")
                
        # Atualiza embeddings para novos termos mapeados que não estão no cache
        self._warmup_embeddings_cache()

    def _warmup_embeddings_cache(self) -> None:
        """Gera em lote os embeddings de termos aprovados recém-adicionados."""
        terms_to_embed = []
        for target, values in self.approved_original_values.items():
            for val in values:
                if val not in self.embeddings_cache:
                    terms_to_embed.append(val)
                    
        if not terms_to_embed:
            return
            
        self._log(f"Gerando embeddings para {len(terms_to_embed)} novos termos aprovados...")
        
        # Chama API do Gemini em lotes de 100
        batch_size = 100
        for i in range(0, len(terms_to_embed), batch_size):
            chunk = terms_to_embed[i:i + batch_size]
            try:
                response = self.client.models.embed_content(
                    model=self.embedding_model,
                    contents=chunk
                )
                for val, emb_data in zip(chunk, response.embeddings):
                    self.embeddings_cache[val] = [float(x) for x in emb_data.values]
            except Exception as e:
                self._log(f"Falha ao obter embeddings de aquecimento: {e}")
                
        self._save_embeddings_cache()

    def _get_embedding(self, text: str) -> list[float] | None:
        """Obtém embedding de um texto, usando cache ou chamando a API."""
        if text in self.embeddings_cache:
            return self.embeddings_cache[text]
            
        try:
            response = self.client.models.embed_content(
                model=self.embedding_model,
                contents=text
            )
            emb = [float(x) for x in response.embeddings[0].values]
            self.embeddings_cache[text] = emb
            self._save_embeddings_cache()
            return emb
        except Exception as e:
            self._log(f"Erro ao obter embedding para '{text}': {e}")
            return None

    def suggest_normalization(self, target: str, raw_value: str) -> dict[str, Any] | None:
        """Sugere a normalização para um valor bruto baseado nos termos aprovados históricos.
        Retorna dicionário com a normalização proposta ou None caso não encontre correspondência confiável.
        """
        if not raw_value or pd.isna(raw_value):
            return None
            
        raw_value = str(raw_value).strip()
        key_raw = remove_accents(raw_value).lower()
        
        # 1. Correspondência Exata
        if target in self.approved_mappings and key_raw in self.approved_mappings[target]:
            norm, cat, subcat = self.approved_mappings[target][key_raw]
            return {
                "valor_original": raw_value,
                "valor_normalizado": norm,
                "categoria": cat,
                "subcategoria": subcat,
                "confianca": "alta",
                "acao_recomendada": "aplicar automático",
                "justificativa": "Correspondência exata com termo aprovado anteriormente.",
                "origem": "ml_exact"
            }
            
        # 2. Similaridade de String (difflib) - Ótimo para pequenos erros de grafia/digitação
        if target in self.approved_original_values:
            best_str_match = None
            best_str_ratio = 0.0
            raw_clean = remove_accents(raw_value).lower()
            for approved_val in self.approved_original_values[target]:
                app_clean = remove_accents(approved_val).lower()
                ratio = difflib.SequenceMatcher(None, raw_clean, app_clean).ratio()
                if ratio > best_str_ratio:
                    best_str_ratio = ratio
                    best_str_match = approved_val
                    
            if best_str_ratio >= self.min_string_similarity and best_str_match:
                key_match = remove_accents(best_str_match).lower()
                norm, cat, subcat = self.approved_mappings[target][key_match]
                return {
                    "valor_original": raw_value,
                    "valor_normalizado": norm,
                    "categoria": cat,
                    "subcategoria": subcat,
                    "confianca": "alta",
                    "acao_recomendada": "aplicar automático",
                    "justificativa": f"Similaridade ortográfica alta ({round(best_str_ratio*100)}%) com '{best_str_match}'.",
                    "origem": "ml_string"
                }

        # 3. Similaridade Semântica (Embeddings + Cosine Similarity)
        raw_emb = self._get_embedding(raw_value)
        if raw_emb and target in self.approved_original_values and self.approved_original_values[target]:
            raw_v = np.array(raw_emb)
            
            best_semantic_match = None
            best_semantic_sim = -1.0
            
            for approved_val in self.approved_original_values[target]:
                app_emb = self.embeddings_cache.get(approved_val)
                if not app_emb:
                    continue
                app_v = np.array(app_emb)
                
                # Cosine Similarity
                sim = float(np.dot(raw_v, app_v) / (np.linalg.norm(raw_v) * np.linalg.norm(app_v)))
                if sim > best_semantic_sim:
                    best_semantic_sim = sim
                    best_semantic_match = approved_val
                    
            if best_semantic_sim >= self.min_semantic_similarity and best_semantic_match:
                key_match = remove_accents(best_semantic_match).lower()
                norm, cat, subcat = self.approved_mappings[target][key_match]
                return {
                    "valor_original": raw_value,
                    "valor_normalizado": norm,
                    "categoria": cat,
                    "subcategoria": subcat,
                    "confianca": "alta" if best_semantic_sim >= 0.93 else "media",
                    "acao_recomendada": "aplicar automático" if best_semantic_sim >= 0.93 else "revisar manualmente",
                    "justificativa": f"Similaridade semântica de {round(best_semantic_sim*100, 1)}% com '{best_semantic_match}'.",
                    "origem": "ml_semantic"
                }

        return None
