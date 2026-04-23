from __future__ import annotations

import re
from typing import Any

from src.shared.config import Settings
from src.shared.ids import stable_hash_id
from src.transformation.cleaning import clean_list, clean_string, clean_year
from src.transformation.normalizers import (
    infer_method_family,
    normalize_document_type,
    normalize_sector,
    normalize_territorial_scope,
)

def gerar_sigla(nome_documento: str | None) -> str:
    if not nome_documento:
        return "S_N"

    stopwords = {
        "de", "do", "da", "dos", "das", "e", "para", "com", "em",
        "no", "na", "o", "a", "os", "as", "the", "of", "and",
    }
    palavras = re.findall(r"\b[A-Za-zÀ-ÿ]+\b", str(nome_documento))
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

    aplicou_estudo_futuro = record.get("aplicou_estudo_futuro")
    if aplicou_estudo_futuro is None:
        aplicou_estudo_futuro = bool(metodos or tipo_estudo_futuro)

    extensao_tempo = None
    if isinstance(ano_publicacao, int) and isinstance(horizonte_temporal, int):
        extensao_tempo = horizonte_temporal - ano_publicacao

    nome_documento_norm = clean_string(nome_documento)
    tipo_documento_norm = normalize_document_type(tipo_documento, settings)
    abrangencia_norm = normalize_territorial_scope(abrangencia, settings)
    setor_norm = normalize_sector(setor, settings)

    familia_metodo_norm = None

    instituicao_responsavel_norm = clean_string(instituicao_responsavel)
    instituicoes_apoio_norm = [clean_string(item) for item in instituicoes_apoio if clean_string(item)]
    temas_norm = [clean_string(item) for item in temas if clean_string(item)]
    metodos_norm = [clean_string(item) for item in metodos if clean_string(item)]

    id_arquivo = stable_hash_id("arq", metadata.get("source_file_hash"), metadata.get("source_file_name"))
    id_documento_logico = stable_hash_id(
        "doc",
        nome_documento_norm or nome_documento or metadata.get("source_file_name"),
        instituicao_responsavel_norm,
        ano_publicacao,
    )

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
        "aplicou_estudo_futuro": aplicou_estudo_futuro,
        "tipo_estudo_futuro": tipo_estudo_futuro,
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
        "flag_revisao_manual": any([
            not nome_documento_norm,
            ano_publicacao is None,
            tipo_documento_norm is None,
        ]),
    }