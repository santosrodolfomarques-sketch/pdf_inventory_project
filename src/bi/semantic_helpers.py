from __future__ import annotations

import ast
import json
import math
import re
import unicodedata
from typing import Any

import pandas as pd


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def strip_accents_lower(value: Any) -> str:
    text = normalize_text(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def coalesce_text(*values: Any, default: str | None = None) -> str | None:
    for value in values:
        text = normalize_text(value)
        if text and text.lower() not in {"nan", "none", "null"}:
            return text
    return default


def safe_parse_list(value: Any) -> list[str]:
    """Converte listas serializadas em listas Python, preservando strings úteis."""
    if value is None:
        return []
    if isinstance(value, float) and math.isnan(value):
        return []
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in {"nan", "none", "null"}:
            return []
        if text.startswith("[") and text.endswith("]"):
            try:
                raw_items = json.loads(text)
            except Exception:
                try:
                    raw_items = ast.literal_eval(text)
                except Exception:
                    raw_items = [text]
        else:
            raw_items = [text]
    else:
        raw_items = [value]

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = normalize_text(item)
        if not text or text.lower() in {"nan", "none", "null"}:
            continue
        key = strip_accents_lower(text)
        if key not in seen:
            seen.add(key)
            cleaned.append(text)
    return cleaned


def choose_scalar(df: pd.DataFrame, base_col: str, default: str | None = None) -> pd.Series:
    """Escolhe coluna normalizada quando existir; caso contrário, usa a coluna bruta."""
    norm_col = f"{base_col}_norm"
    if norm_col in df.columns and base_col in df.columns:
        chosen = df[norm_col].where(df[norm_col].notna() & (df[norm_col].astype(str).str.strip() != ""), df[base_col])
    elif norm_col in df.columns:
        chosen = df[norm_col]
    elif base_col in df.columns:
        chosen = df[base_col]
    else:
        chosen = pd.Series([default] * len(df), index=df.index)

    chosen = chosen.apply(lambda value: coalesce_text(value, default=default))
    if default is not None:
        chosen = chosen.fillna(default)
    return chosen


def choose_list(df: pd.DataFrame, base_col: str) -> pd.Series:
    """Escolhe lista normalizada quando existir; caso contrário, usa lista bruta."""
    norm_col = f"{base_col}_norm"
    source_col = norm_col if norm_col in df.columns else base_col
    if source_col not in df.columns:
        return pd.Series([[] for _ in range(len(df))], index=df.index)
    return df[source_col].apply(safe_parse_list)


def classify_macrotema(tema: Any) -> str:
    text = strip_accents_lower(tema)
    rules = [
        ("Meio Ambiente e Clima", ["clima", "climate", "ambient", "environment", "floresta", "desmat", "oceano", "biodivers", "ecossistema", "sustentab", "residuo", "carbon", "energia"]),
        ("Desenvolvimento Social", ["pobreza", "fome", "hunger", "saude", "health", "educacao", "education", "genero", "gender", "desigual", "inequal", "direitos humanos", "violencia", "voluntariado"]),
        ("Economia e Trabalho", ["econom", "growth", "trabalho", "emprego", "renda", "produt", "industr", "capital", "mercado"]),
        ("Governança e Instituições", ["govern", "democr", "politica publica", "public policy", "institu", "paz", "peace", "justica", "multilateral", "transpar", "seguranca publica"]),
        ("Ciência, Tecnologia e Inovação", ["ciencia", "science", "tecnolog", "inov", "innovation", "inteligencia artificial", "ia", "i.a", "digital", "realidade virtual", "cidades inteligentes"]),
        ("Agenda 2030 e ODS", ["ods", "sdg", "sustainable development goals", "agenda 2030", "2030 agenda"]),
    ]
    for macrotema, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return macrotema
    return "Outros / Não Classificado"


def classify_subtema(tema: Any) -> str:
    text = strip_accents_lower(tema)
    rules = [
        ("Clima", ["clima", "climate", "carbon", "emisso"]),
        ("Biodiversidade e Ecossistemas", ["biodivers", "ecossistema", "floresta", "desmat", "ocean", "marine"]),
        ("Energia", ["energia", "energy"]),
        ("Pobreza e Desigualdade", ["pobreza", "desigual", "inequal", "hunger", "fome"]),
        ("Saúde", ["saude", "health", "covid"]),
        ("Educação", ["educacao", "education"]),
        ("Gênero e Diversidade", ["genero", "gender", "mulher", "racismo", "indigena", "quilombola"]),
        ("Governança", ["govern", "democr", "institu", "multilateral"]),
        ("Tecnologia", ["tecnolog", "digital", "inteligencia artificial", "ia", "i.a", "virtual"]),
        ("ODS / Agenda 2030", ["ods", "sdg", "agenda 2030", "sustainable development goals"]),
    ]
    for subtema, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return subtema
    return "Outros"


def classify_method_family(metodo: Any, familia_hint: Any = None) -> str:
    hint = coalesce_text(familia_hint)
    if hint:
        return hint
    text = strip_accents_lower(metodo)
    rules = [
        ("Extrapolação de Tendências", ["tendencia", "trend", "series temporais", "forecast", "previs", "projecao", "projeção"]),
        ("Cenários Prospectivos", ["cenario", "cenário", "scenario", "prospectiv", "foresight"]),
        ("Painel de Especialistas", ["delphi", "workshop", "grupo focal", "focus group", "painel", "especialista", "consulta"]),
        ("Modelagem e Simulação Quantitativa", ["modelagem", "simulacao", "simulação", "modelo", "econometr", "microssimul"]),
        ("Visão de Futuro / Backcasting", ["backcasting", "visao de futuro", "visão de futuro", "roadmap"]),
        ("Monitoramento e Indicadores", ["indicador", "monitoramento", "avaliacao", "avaliação", "meta", "classificacao", "classificação"]),
        ("Revisão Bibliográfica / Documental", ["bibliograf", "documental", "literatura", "referencia", "scielo", "capes"]),
    ]
    for family, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return family
    return "Outros / Não Classificado"


def classify_method_nature(familia: Any, metodo: Any = None) -> str:
    text = strip_accents_lower(f"{familia or ''} {metodo or ''}")
    if any(k in text for k in ["modelagem", "simulacao", "quantit", "indicador", "series", "forecast"]):
        return "Quantitativo"
    if any(k in text for k in ["delphi", "workshop", "grupo focal", "painel", "entrevista", "consulta"]):
        return "Qualitativo"
    if any(k in text for k in ["cenario", "prospect", "foresight", "backcasting"]):
        return "Prospectivo"
    if any(k in text for k in ["bibliograf", "documental", "literatura"]):
        return "Documental"
    return "Não Classificado"


def quality_level(score: float) -> str:
    if score >= 0.80:
        return "Alta"
    if score >= 0.55:
        return "Média"
    if score >= 0.35:
        return "Baixa"
    return "Crítica"
