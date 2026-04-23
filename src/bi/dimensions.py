from __future__ import annotations

import json
from typing import Any

import pandas as pd

from src.bi.bridges import build_simple_dimension, explode_dimension_with_bridge
from src.shared.ids import stable_hash_id

LIST_COLUMNS = [
    "temas_norm",
    "metodos_estudo_futuro_norm",
    "instituicoes_apoio_norm",
    "referencias",
    "condicionantes_estudo_futuro",
    "source_files",
]

def deserialize_list_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for column in LIST_COLUMNS:
        if column in df.columns:
            df[column] = df[column].apply(
                lambda value: json.loads(value) if isinstance(value, str) and value.strip().startswith("[") else []
            )
    return df

def build_document_dimension(df: pd.DataFrame) -> pd.DataFrame:
    dim = df[[
        "id_documento_logico",
        "nome_documento_norm",
        "sigla_ou_abreviacao",
        "tipo_documento_norm",
        "instituicao_responsavel_norm",
        "qtd_arquivos_origem",
    ]].drop_duplicates().rename(columns={
        "id_documento_logico": "id_documento",
        "nome_documento_norm": "nome_documento",
        "tipo_documento_norm": "tipo_documento",
        "instituicao_responsavel_norm": "instituicao_responsavel",
    })
    return dim.reset_index(drop=True)

def build_time_dimension(df: pd.DataFrame) -> pd.DataFrame:
    dim = (
        df[["ano_publicacao", "horizonte_temporal", "extensao_tempo"]]
        .drop_duplicates()
        .dropna(how="all")
        .reset_index(drop=True)
    )
    dim["id_tempo"] = [
        stable_hash_id("tmp", row.ano_publicacao, row.horizonte_temporal, row.extensao_tempo)
        for row in dim.itertuples(index=False)
    ]
    return dim[["id_tempo", "ano_publicacao", "horizonte_temporal", "extensao_tempo"]]

def build_dimensions_and_bridges(df_raw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    df = deserialize_list_columns(df_raw)

    dim_documento = build_document_dimension(df)
    dim_tempo = build_time_dimension(df)
    dim_setor = build_simple_dimension(df, "setor_norm", "set", "setor")
    dim_abrangencia = build_simple_dimension(df, "abrangencia_territorial_norm", "abr", "abrangencia")
    dim_instituicao_responsavel = build_simple_dimension(df, "instituicao_responsavel_norm", "ins", "instituicao")

    dim_tema, ponte_tema = explode_dimension_with_bridge(df, "id_documento_logico", "temas_norm", "tema", "tem")
    dim_metodo, ponte_metodo = explode_dimension_with_bridge(df, "id_documento_logico", "metodos_estudo_futuro_norm", "metodo", "met")
    dim_apoio, ponte_apoio = explode_dimension_with_bridge(df, "id_documento_logico", "instituicoes_apoio_norm", "instituicao_apoio", "iap")
    dim_ref, ponte_ref = explode_dimension_with_bridge(df, "id_documento_logico", "referencias", "referencia", "ref")
    dim_cond, ponte_cond = explode_dimension_with_bridge(df, "id_documento_logico", "condicionantes_estudo_futuro", "condicionante", "con")
    dim_source_file, ponte_source_file = explode_dimension_with_bridge(df, "id_documento_logico", "source_files", "arquivo_origem", "src")

    dim_metodologia = (
        df[[
            "familia_do_metodo_norm",
            "tipo_estudo_futuro",
            "aplicou_estudo_futuro",
        ]]
        .drop_duplicates()
        .reset_index(drop=True)
        .rename(columns={"familia_do_metodo_norm": "familia_do_metodo"})
    )
    dim_metodologia["id_metodologia"] = [
        stable_hash_id("mdg", row.familia_do_metodo, row.tipo_estudo_futuro, row.aplicou_estudo_futuro)
        for row in dim_metodologia.itertuples(index=False)
    ]

    return {
        "dim_documento": dim_documento,
        "dim_tempo": dim_tempo,
        "dim_setor": dim_setor,
        "dim_abrangencia": dim_abrangencia,
        "dim_instituicao_responsavel": dim_instituicao_responsavel,
        "dim_tema": dim_tema,
        "dim_metodo": dim_metodo,
        "dim_apoio": dim_apoio,
        "dim_referencia": dim_ref,
        "dim_condicionante": dim_cond,
        "dim_source_file": dim_source_file,
        "dim_metodologia": dim_metodologia,
        "ponte_documento_tema": ponte_tema,
        "ponte_documento_metodo": ponte_metodo,
        "ponte_documento_instituicao_apoio": ponte_apoio,
        "ponte_documento_referencia": ponte_ref,
        "ponte_documento_condicionante": ponte_cond,
        "ponte_documento_arquivo_origem": ponte_source_file,
    }
