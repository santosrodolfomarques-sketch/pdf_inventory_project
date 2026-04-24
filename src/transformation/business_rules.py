from __future__ import annotations

import re
from typing import Any

from src.shared.config import Settings
from src.shared.ids import stable_hash_id
from src.transformation.cleaning import clean_list, clean_string, clean_year
from src.transformation.normalizers import (
    infer_aplicou_estudo_futuro,
    infer_method_family,
    normalize_document_type,
    normalize_institution,
    normalize_method_list,
    normalize_sector,
    normalize_study_type,
    normalize_theme_list,
    normalize_territorial_scope,
)


def gerar_sigla(nome_documento: str | None) -> str:
    if not nome_documento:
        return "S_N"

    stopwords = {
        "de", "do", "da", "dos", "das", "e", "para", "com", "em",
        "no", "na", "o", "a", "os", "as", "the", "of", "and",
    }
    palavras = re.findall(r"\b[A-Za-zÀ-ÿ0-9]+\b", str(nome_documento))
    iniciais = [palavra[0].upper() for palavra in palavras if palavra.lower() not in stopwords]
    return "".join(iniciais[:12]) or "S_N"


def apply_business_rules(record: dict[str, Any], metadata: dict[str, Any], settings: Settings) -> dict[str, Any]:
    nome_documento = clean_string(record.get("nome_documento"))
    tipo_documento = clean_string(record.get("tipo_documento"))
    ano_publicacao = clean_year(record.get("ano_publicacao"))
    horizonte_temporal = clean_year(record.get("horizonte_temporal"))
    abrangencia = clean_string(record.get("abrangencia_territorial"))
    setor = clean_string(record.get("setor"))
    tipo_estudo_futuro = clean_string(record.get("tipo_estudo_futuro"))
    instituicao_responsavel = clean_string(record.get("instituicao_responsavel"))

    temas = clean_list(record.get("temas"))
    metodos = clean_list(record.get("metodos_estudo_futuro"))
    referencias = clean_list(record.get("referencias"))
    condicionantes = clean_list(record.get("condicionantes_estudo_futuro"))
    instituicoes_apoio = clean_list(record.get("instituicoes_apoio"))

    aplicou_extraido = record.get("aplicou_estudo_futuro")
    aplicou_estudo_futuro = infer_aplicou_estudo_futuro(
        extracted_flag=aplicou_extraido,
        nome_documento=nome_documento,
        horizonte_temporal=horizonte_temporal,
        tipo_estudo_futuro=tipo_estudo_futuro,
        metodos=metodos,
    )

    extensao_tempo = None
    if isinstance(ano_publicacao, int) and isinstance(horizonte_temporal, int):
        extensao_tempo = horizonte_temporal - ano_publicacao

    nome_documento_norm = clean_string(nome_documento)
    tipo_documento_norm = normalize_document_type(tipo_documento, settings)
    abrangencia_norm = normalize_territorial_scope(abrangencia, settings)
    setor_norm = normalize_sector(setor, settings)
    tipo_estudo_futuro_norm = normalize_study_type(tipo_estudo_futuro, settings)
    temas_norm = normalize_theme_list(temas, settings)
    metodos_norm = normalize_method_list(metodos, settings)
    familia_metodo_norm = infer_method_family(
        metodos=metodos_norm or metodos,
        tipo_estudo_futuro=tipo_estudo_futuro_norm or tipo_estudo_futuro,
        settings=settings,
    )
    instituicao_responsavel_norm = normalize_institution(instituicao_responsavel, settings)
    instituicoes_apoio_norm = [
        normalized for normalized in (normalize_institution(item, settings) for item in instituicoes_apoio) if normalized
    ]

    id_arquivo = stable_hash_id("arq", metadata.get("source_file_hash"), metadata.get("source_file_name"))
    id_documento_logico = stable_hash_id(
        "doc",
        nome_documento_norm or nome_documento or metadata.get("source_file_name"),
        instituicao_responsavel_norm or instituicao_responsavel,
        ano_publicacao,
    )

    flag_revisao_manual = any([
        not nome_documento_norm,
        ano_publicacao is None,
        tipo_documento_norm is None,
        aplicou_estudo_futuro is None,
        bool(horizonte_temporal and not abrangencia_norm),
    ])

    return {
        "id_arquivo": id_arquivo,
        "id_documento_logico": id_documento_logico,
        "source_file_name": metadata.get("source_file_name"),
        "source_file_hash": metadata.get("source_file_hash"),
        "processed_at_utc": metadata.get("processed_at_utc"),
        "nome_documento": nome_documento,
        "nome_documento_norm": nome_documento_norm,
        "sigla_ou_abreviacao": gerar_sigla(nome_documento_norm),
        "tipo_documento": tipo_documento,
        "tipo_documento_norm": tipo_documento_norm,
        "ano_publicacao": ano_publicacao,
        "horizonte_temporal": horizonte_temporal,
        "extensao_tempo": extensao_tempo,
        "abrangencia_territorial": abrangencia,
        "abrangencia_territorial_norm": abrangencia_norm,
        "setor": setor,
        "setor_norm": setor_norm,
        "temas": temas,
        "temas_norm": temas_norm,
        "aplicou_estudo_futuro_extraido": aplicou_extraido,
        "aplicou_estudo_futuro": aplicou_estudo_futuro,
        "tipo_estudo_futuro": tipo_estudo_futuro,
        "tipo_estudo_futuro_norm": tipo_estudo_futuro_norm,
        "metodos_estudo_futuro": metodos,
        "metodos_estudo_futuro_norm": metodos_norm,
        "familia_do_metodo": None,
        "familia_do_metodo_norm": familia_metodo_norm,
        "instituicao_responsavel": instituicao_responsavel,
        "instituicao_responsavel_norm": instituicao_responsavel_norm,
        "instituicoes_apoio": instituicoes_apoio,
        "instituicoes_apoio_norm": instituicoes_apoio_norm,
        "referencias": referencias,
        "condicionantes_estudo_futuro": condicionantes,
        "flag_revisao_manual": flag_revisao_manual,
    }
