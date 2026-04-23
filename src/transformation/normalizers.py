from __future__ import annotations

from src.shared.config import Settings
from src.shared.utils import remove_accents_lower

def normalize_with_map(value: str | None, mapping: dict[str, str]) -> str | None:
    if not value:
        return None
    key = remove_accents_lower(value)
    if key in mapping:
        return mapping[key]

    for raw_key, mapped_value in mapping.items():
        if raw_key in key:
            return mapped_value

    return value.strip()

def normalize_document_type(value: str | None, settings: Settings) -> str | None:
    return normalize_with_map(value, settings.document_type_map)

def normalize_territorial_scope(value: str | None, settings: Settings) -> str | None:
    return normalize_with_map(value, settings.territorial_scope_map)

def normalize_sector(value: str | None, settings: Settings) -> str | None:
    return normalize_with_map(value, settings.sector_map)

def infer_method_family(
    metodos: list[str] | None,
    tipo_estudo_futuro: str | None,
    settings: Settings,
) -> str | None:
    textos = []

    if metodos:
        textos.extend(metodos)
    if tipo_estudo_futuro:
        textos.append(tipo_estudo_futuro)

    if not textos:
        return None

    texto_base = " | ".join(remove_accents_lower(t) for t in textos if t)

    regras = [
        (
            "Extrapolação de Tendências",
            ["tendencia", "trend", "series temporais", "forecast", "projecao", "projeção"],
        ),
        (
            "Cenários Prospectivos",
            ["cenario", "cenário", "scenario", "foresight", "prospectiv"],
        ),
        (
            "Painel de Especialistas (Delphi/Workshops)",
            ["delphi", "workshop", "painel de especialistas", "especialistas", "consulta a especialistas"],
        ),
        (
            "Modelagem e Simulação Quantitativa",
            ["modelagem", "simulacao", "simulação", "modelo econometrico", "microssimulacao", "microssimulação"],
        ),
        (
            "Visão de Futuro / Backcasting",
            ["backcasting", "visao de futuro", "visão de futuro", "future vision", "roadmap"],
        ),
        (
            "Análise de Impacto Cruzado",
            ["impacto cruzado", "cross-impact", "cross impact"],
        ),
    ]

    for familia, palavras_chave in regras:
        if any(chave in texto_base for chave in palavras_chave):
            return familia

    return "Outros"