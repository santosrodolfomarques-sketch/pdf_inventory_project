from __future__ import annotations

import re
from typing import Iterable

from src.shared.config import Settings
from src.shared.utils import normalize_whitespace, remove_accents_lower, union_unique_preserve_order


def normalize_with_map(value: str | None, mapping: dict[str, str]) -> str | None:
    if not value:
        return None
    key = remove_accents_lower(value)
    if key in mapping:
        return mapping[key]

    for raw_key, mapped_value in mapping.items():
        if raw_key in key:
            return mapped_value

    cleaned = normalize_whitespace(value)
    return cleaned


def normalize_document_type(value: str | None, settings: Settings) -> str | None:
    return normalize_with_map(value, settings.document_type_map)


def normalize_territorial_scope(value: str | None, settings: Settings) -> str | None:
    return normalize_with_map(value, settings.territorial_scope_map)


def normalize_sector(value: str | None, settings: Settings) -> str | None:
    return normalize_with_map(value, settings.sector_map)


def normalize_institution(value: str | None, settings: Settings) -> str | None:
    return normalize_with_map(value, settings.institution_map)


def normalize_study_type(value: str | None, settings: Settings) -> str | None:
    return normalize_with_map(value, settings.future_study_type_map)


def normalize_theme(value: str | None, settings: Settings) -> str | None:
    if not value:
        return None
    normalized = normalize_with_map(value, settings.theme_map)
    if not normalized:
        return None

    text = normalize_whitespace(normalized)
    if not text:
        return None

    key = remove_accents_lower(text)
    repairs = {
        "i.a. virturealidade": "IA e Virtualidade",
        "ia virturealidade": "IA e Virtualidade",
        "virturealidade": "Virtualidade",
        "reduce inequity": "Redução das Desigualdades",
        "sustainable standards of production and consumption": "Consumo e Produção Sustentáveis",
        "cities and human communities": "Cidades e Comunidades Sustentáveis",
        "affordable, modern and sustainable energy": "Energia Limpa e Acessível",
        "infrastructure, industrialization and innovation": "Indústria, Inovação e Infraestrutura",
        "peaceful and inclusive societies": "Paz, Justiça e Instituições Eficazes",
        "global partnership for sustainable development": "Parcerias para o Desenvolvimento Sustentável",
        "terrestrial ecosystem use": "Vida Terrestre",
        "oceans, seas and marine resources": "Vida na Água",
    }
    return repairs.get(key, text)


def normalize_theme_list(values: Iterable[str] | None, settings: Settings) -> list[str]:
    if not values:
        return []
    cleaned = []
    for value in values:
        item = normalize_theme(value, settings)
        if item:
            cleaned.append(item)
    return union_unique_preserve_order(cleaned)


def normalize_method(value: str | None, settings: Settings) -> str | None:
    return normalize_with_map(value, settings.method_map)


def normalize_method_list(values: Iterable[str] | None, settings: Settings) -> list[str]:
    if not values:
        return []
    cleaned = []
    for value in values:
        item = normalize_method(value, settings)
        if item:
            cleaned.append(item)
    return union_unique_preserve_order(cleaned)


def infer_method_family(
    metodos: list[str] | None,
    tipo_estudo_futuro: str | None,
    settings: Settings,
) -> str | None:
    texts = []
    if metodos:
        texts.extend(metodos)
    if tipo_estudo_futuro:
        texts.append(tipo_estudo_futuro)

    if not texts:
        return None

    corpus = " | ".join(remove_accents_lower(item) for item in texts if item)

    rules = [
        (
            "Extrapolação de Tendências",
            ["tendencia", "forecast", "projecao", "projeção", "series temporais", "indicadores", "monitoramento"],
        ),
        (
            "Cenários Prospectivos",
            ["cenario", "cenário", "scenario", "foresight", "prospectiv"],
        ),
        (
            "Painel de Especialistas (Delphi/Workshops)",
            ["delphi", "workshop", "grupo focal", "painel de especialistas", "especialistas", "consulta a especialistas"],
        ),
        (
            "Modelagem e Simulação Quantitativa",
            ["modelagem", "simulacao", "simulação", "econometr", "microssimul", "dados oficiais", "indicador"],
        ),
        (
            "Visão de Futuro / Backcasting",
            ["backcasting", "visao de futuro", "visão de futuro", "future vision", "roadmap", "visao estrategica"],
        ),
        (
            "Análise de Impacto Cruzado",
            ["impacto cruzado", "cross-impact", "cross impact"],
        ),
    ]

    for family, keywords in rules:
        if any(keyword in corpus for keyword in keywords):
            return family

    return "Outros"


def infer_aplicou_estudo_futuro(
    extracted_flag: bool | None,
    nome_documento: str | None,
    horizonte_temporal: int | None,
    tipo_estudo_futuro: str | None,
    metodos: list[str] | None,
) -> bool | None:
    method_count = len(metodos or [])
    textual_corpus = " | ".join(
        item for item in [nome_documento or "", tipo_estudo_futuro or ""] + (metodos or []) if item
    )
    corpus = remove_accents_lower(textual_corpus)

    strong_signals = [
        "cenario", "cenário", "forecast", "foresight", "backcasting", "delphi",
        "modelagem", "simulacao", "simulação", "projecao", "projeção", "monitoramento", "avaliacao",
        "avaliação", "indicadores", "grupo focal", "painel de especialistas",
    ]
    weak_signals = ["futuro", "future", "vision", "visao", "visão", "2050", "2030"]

    if method_count >= 1:
        return True
    if tipo_estudo_futuro and any(signal in corpus for signal in strong_signals):
        return True
    if extracted_flag is False and not any(signal in corpus for signal in strong_signals):
        return False
    if extracted_flag is True and any(signal in corpus for signal in strong_signals):
        return True
    if extracted_flag is True and any(signal in corpus for signal in weak_signals):
        return None
    if horizonte_temporal and horizonte_temporal >= 2030 and any(signal in corpus for signal in weak_signals):
        return None
    return extracted_flag
