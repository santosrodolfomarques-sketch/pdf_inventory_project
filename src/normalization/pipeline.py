from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.config import Settings
from src.normalization.normalizer import build_ai_dictionaries
from src.shared.utils import to_json_string
from src.transformation.cleansing import remove_accents

# Mapeamento de colunas escalares: dicionario_alvo -> (coluna_bruta, coluna_normalizada)
SCALAR_FIELDS = {
    "setor": ("setor", "setor_norm"),
    "tipo_documento": ("tipo_documento", "tipo_documento_norm"),
    "abrangencia_territorial": ("abrangencia_territorial", "abrangencia_territorial_norm"),
    "tipo_estudo_futuro": ("tipo_estudo_futuro", "tipo_estudo_futuro_norm"),
    "instituicao_responsavel": ("instituicao_responsavel", "instituicao_responsavel_norm"),
}

# Mapeamento de colunas do tipo lista: dicionario_alvo -> (coluna_bruta, coluna_normalizada)
LIST_FIELDS = {
    "instituicao_responsavel": ("instituicoes_apoio", "instituicoes_apoio_norm"),
    "condicionantes": ("condicionantes_estudo_futuro", "condicionantes_estudo_futuro_norm"),
}


def _load_dictionary(path: Path) -> dict[str, str]:
    """Carrega o dicionário CSV e mapeia valor original para valor normalizado se aprovado."""
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    if df.empty:
        return {}

    # Aplica apenas linhas aprovadas para aplicação automática
    df_approved = df[df["aplicar_automaticamente"].astype(str).str.lower().isin(["true", "1", "sim", "yes"])]

    mapping = {}
    for _, row in df_approved.iterrows():
        orig = str(row.get("valor_original", "")).strip()
        norm = row.get("valor_normalizado")
        if orig and pd.notna(norm):
            key = remove_accents(orig).lower()
            mapping[key] = str(norm).strip()
    return mapping


def _safe_deserialize_list(val: Any) -> list[str]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []
    if isinstance(val, list):
        return val
    text = str(val).strip()
    if not text or text.lower() in {"nan", "none", "null", "[]"}:
        return []
    try:
        loaded = json.loads(text)
        return loaded if isinstance(loaded, list) else [loaded]
    except Exception:
        return [text]


def _apply_scalar(value: Any, mapping: dict[str, str]) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return value
    key = remove_accents(str(value)).lower()
    return mapping.get(key, value)


def _apply_list(value: Any, mapping: dict[str, str]) -> list[str]:
    items = _safe_deserialize_list(value)
    normalized = []
    seen = set()
    for item in items:
        mapped = _apply_scalar(item, mapping)
        marker = remove_accents(str(mapped)).lower()
        if marker not in seen:
            seen.add(marker)
            normalized.append(mapped)
    return normalized


def apply_ai_dictionaries(settings: Settings, logger: Any) -> dict[str, Any]:
    """Aplica as propostas aprovadas de normalização em todas as tabelas tratadas e consolidadas."""
    settings.ai_applied_dir.mkdir(parents=True, exist_ok=True)

    sources = {
        "documentos_tratados.csv": settings.transformed_base_dir / "documentos_tratados.csv",
        "documentos_consolidados.csv": settings.transformed_base_dir / "documentos_consolidados.csv",
    }

    # Carrega todos os dicionários em memória
    mappings = {}
    for dict_name in ["setor", "tipo_documento", "abrangencia_territorial", "tipo_estudo_futuro", "instituicao_responsavel", "condicionantes"]:
        path = settings.ai_dictionary_dir / f"dicionario_{dict_name}.csv"
        mappings[dict_name] = _load_dictionary(path)

    outputs = {}

    for filename, path in sources.items():
        if not path.exists():
            logger.warning(f"Tabela base para aplicação não encontrada: {path.name}")
            continue

        df = pd.read_csv(path)
        if df.empty:
            continue

        df_norm = df.copy()

        # Aplica colunas escalares
        for dict_name, (bruto, norm) in SCALAR_FIELDS.items():
            m = mappings.get(dict_name, {})
            if m and bruto in df_norm.columns:
                df_norm[norm] = df_norm[bruto].apply(lambda x: _apply_scalar(x, m))

        # Aplica colunas de listas
        for dict_name, (bruto, norm) in LIST_FIELDS.items():
            m = mappings.get(dict_name, {})
            if bruto in df_norm.columns:
                df_norm[norm] = df_norm[bruto].apply(lambda x: to_json_string(_apply_list(x, m)))

        # Especial: temas e métodos são do tipo lista de normalização própria
        theme_map = mappings.get("temas", {})
        if "temas" in df_norm.columns:
            df_norm["temas_norm"] = df_norm["temas"].apply(lambda x: to_json_string(_apply_list(x, theme_map)))

        method_map = mappings.get("metodos", {})
        if "metodos_estudo_futuro" in df_norm.columns:
            df_norm["metodos_estudo_futuro_norm"] = df_norm["metodos_estudo_futuro"].apply(
                lambda x: to_json_string(_apply_list(x, method_map))
            )

        # Copia condicionantes normalizadas na coluna _norm (para BI)
        cond_map = mappings.get("condicionantes", {})
        if "condicionantes_estudo_futuro" in df_norm.columns:
            df_norm["condicionantes_estudo_futuro_norm"] = df_norm["condicionantes_estudo_futuro"].apply(
                lambda x: to_json_string(_apply_list(x, cond_map))
            )

        # Salva o arquivo normalizado
        out_path = settings.ai_applied_dir / filename.replace(".csv", "_normalizado_ia.csv")
        df_norm.to_csv(out_path, index=False, encoding="utf-8-sig")
        outputs[filename] = str(out_path)

    logger.info("Aplicação de dicionários de normalização concluída com sucesso.")
    return {"status": "ok", "outputs": outputs}


def run_ai_normalization(
    settings: Settings,
    logger: Any,
    targets: list[str] | None = None,
    only_new_values: bool = False,
) -> dict[str, Any]:
    """Orquestração geral da etapa de normalização por IA."""
    return build_ai_dictionaries(settings, logger, targets, only_new_values)
