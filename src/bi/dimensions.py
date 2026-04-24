from __future__ import annotations

import pandas as pd

from src.bi.bridges import build_simple_dimension, explode_dimension_with_bridge
from src.bi.semantic_helpers import (
    choose_list,
    choose_scalar,
    classify_macrotema,
    classify_method_family,
    classify_method_nature,
    classify_subtema,
    coalesce_text,
    quality_level,
    safe_parse_list,
)
from src.shared.ids import stable_hash_id

LIST_COLUMNS = [
    "temas",
    "temas_norm",
    "metodos_estudo_futuro",
    "metodos_estudo_futuro_norm",
    "instituicoes_apoio",
    "instituicoes_apoio_norm",
    "referencias",
    "condicionantes_estudo_futuro",
    "source_files",
]


def prepare_bi_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Prepara a base para BI priorizando colunas normalizadas e criando listas canônicas."""
    df = df_raw.copy()

    for column in LIST_COLUMNS:
        if column in df.columns:
            df[column] = df[column].apply(safe_parse_list)

    df["bi_nome_documento"] = choose_scalar(df, "nome_documento", "Não informado")
    df["bi_tipo_documento"] = choose_scalar(df, "tipo_documento", "Não informado")
    df["bi_setor"] = choose_scalar(df, "setor", "Não informado")
    df["bi_abrangencia"] = choose_scalar(df, "abrangencia_territorial", "Não informado")
    df["bi_instituicao_responsavel"] = choose_scalar(df, "instituicao_responsavel", "Não informado")
    df["bi_tipo_estudo_futuro"] = choose_scalar(df, "tipo_estudo_futuro", "Não informado")
    df["bi_familia_do_metodo"] = choose_scalar(df, "familia_do_metodo", "Não classificado")

    df["bi_temas"] = choose_list(df, "temas")
    df["bi_metodos"] = choose_list(df, "metodos_estudo_futuro")
    df["bi_instituicoes_apoio"] = choose_list(df, "instituicoes_apoio")

    if "referencias" not in df.columns:
        df["referencias"] = [[] for _ in range(len(df))]
    if "condicionantes_estudo_futuro" not in df.columns:
        df["condicionantes_estudo_futuro"] = [[] for _ in range(len(df))]
    if "source_files" not in df.columns:
        df["source_files"] = [[] for _ in range(len(df))]

    df["referencias"] = df["referencias"].apply(safe_parse_list)
    df["condicionantes_estudo_futuro"] = df["condicionantes_estudo_futuro"].apply(safe_parse_list)
    df["source_files"] = df["source_files"].apply(safe_parse_list)

    return df


# Compatibilidade com facts.py antigo ou outros módulos que ainda importem esta função.
def deserialize_list_columns(df: pd.DataFrame) -> pd.DataFrame:
    return prepare_bi_dataframe(df)


def build_document_dimension(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "id_documento_logico",
        "bi_nome_documento",
        "sigla_ou_abreviacao",
        "bi_tipo_documento",
        "bi_instituicao_responsavel",
        "qtd_arquivos_origem",
    ]
    existing = [col for col in cols if col in df.columns]
    dim = df[existing].drop_duplicates().rename(columns={
        "id_documento_logico": "id_documento",
        "bi_nome_documento": "nome_documento",
        "bi_tipo_documento": "tipo_documento",
        "bi_instituicao_responsavel": "instituicao_responsavel",
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


def build_theme_dimension_and_bridge(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = df[["id_documento_logico", "bi_temas"]].explode("bi_temas").dropna()
    base = base[base["bi_temas"].astype(str).str.strip() != ""]
    base = base.rename(columns={"bi_temas": "tema"})

    dim = base[["tema"]].drop_duplicates().reset_index(drop=True)
    dim["macrotema"] = dim["tema"].apply(classify_macrotema)
    dim["subtema"] = dim["tema"].apply(classify_subtema)
    dim["id_tema"] = [stable_hash_id("tem", row.tema) for row in dim.itertuples(index=False)]
    dim = dim[["id_tema", "tema", "macrotema", "subtema"]]

    ponte = base.merge(dim[["id_tema", "tema"]], on="tema", how="left")[["id_documento_logico", "id_tema"]].drop_duplicates()
    return dim, ponte


def build_method_dimension_and_bridge(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = df[["id_documento_logico", "bi_metodos", "bi_familia_do_metodo"]].explode("bi_metodos").dropna()
    base = base[base["bi_metodos"].astype(str).str.strip() != ""]
    base = base.rename(columns={"bi_metodos": "metodo"})

    dim = base[["metodo", "bi_familia_do_metodo"]].drop_duplicates().reset_index(drop=True)
    dim["familia_do_metodo"] = dim.apply(
        lambda row: classify_method_family(row["metodo"], row.get("bi_familia_do_metodo")),
        axis=1,
    )
    dim["natureza_metodo"] = dim.apply(
        lambda row: classify_method_nature(row["familia_do_metodo"], row["metodo"]),
        axis=1,
    )
    dim["id_metodo"] = [stable_hash_id("met", row.metodo, row.familia_do_metodo) for row in dim.itertuples(index=False)]
    dim = dim[["id_metodo", "metodo", "familia_do_metodo", "natureza_metodo"]]

    ponte = base.merge(dim[["id_metodo", "metodo"]], on="metodo", how="left")[["id_documento_logico", "id_metodo"]].drop_duplicates()
    return dim, ponte


def build_quality_dimension(df: pd.DataFrame) -> pd.DataFrame:
    quality_rows = []
    for row in df.itertuples(index=False):
        qtd_temas = len(getattr(row, "bi_temas", []) or [])
        qtd_metodos = len(getattr(row, "bi_metodos", []) or [])
        qtd_referencias = len(getattr(row, "referencias", []) or [])
        possui_nome = bool(coalesce_text(getattr(row, "bi_nome_documento", None)))
        possui_ano = pd.notna(getattr(row, "ano_publicacao", None))
        possui_horizonte = pd.notna(getattr(row, "horizonte_temporal", None))
        possui_setor = coalesce_text(getattr(row, "bi_setor", None)) not in {None, "Não informado"}
        possui_abrangencia = coalesce_text(getattr(row, "bi_abrangencia", None)) not in {None, "Não informado"}
        aplicou_estudo = bool(getattr(row, "aplicou_estudo_futuro", False))

        score = 0.0
        score += 0.15 if possui_nome else 0
        score += 0.12 if possui_ano else 0
        score += 0.10 if possui_horizonte else 0
        score += 0.10 if possui_setor else 0
        score += 0.08 if possui_abrangencia else 0
        score += 0.15 if qtd_temas > 0 else 0
        score += 0.15 if qtd_referencias > 0 else 0
        score += 0.15 if (not aplicou_estudo or qtd_metodos > 0) else 0
        score = min(round(score, 3), 1.0)

        motivos = []
        if not possui_nome:
            motivos.append("nome_documento_ausente")
        if not possui_ano:
            motivos.append("ano_publicacao_ausente")
        if aplicou_estudo and qtd_metodos == 0:
            motivos.append("estudo_futuro_sem_metodo")
        if not possui_setor:
            motivos.append("setor_nao_informado")
        if not possui_abrangencia:
            motivos.append("abrangencia_nao_informada")

        flag_revisao_manual = bool(getattr(row, "flag_revisao_manual", False)) or bool(motivos)
        id_documento = getattr(row, "id_documento_logico")
        quality_rows.append({
            "id_documento_logico": id_documento,
            "id_qualidade": stable_hash_id("qlt", id_documento, score, "|".join(motivos)),
            "score_qualidade": score,
            "nivel_qualidade": quality_level(score),
            "flag_revisao_manual": flag_revisao_manual,
            "motivos_revisao": "; ".join(motivos) if motivos else "",
        })

    return pd.DataFrame(quality_rows).drop_duplicates().reset_index(drop=True)


def build_dimensions_and_bridges(df_raw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    df = prepare_bi_dataframe(df_raw)

    dim_documento = build_document_dimension(df)
    dim_tempo = build_time_dimension(df)
    dim_setor = build_simple_dimension(df, "bi_setor", "set", "setor")
    dim_abrangencia = build_simple_dimension(df, "bi_abrangencia", "abr", "abrangencia")
    dim_instituicao_responsavel = build_simple_dimension(df, "bi_instituicao_responsavel", "ins", "instituicao")

    dim_tema, ponte_tema = build_theme_dimension_and_bridge(df)
    dim_metodo, ponte_metodo = build_method_dimension_and_bridge(df)
    dim_apoio, ponte_apoio = explode_dimension_with_bridge(df, "id_documento_logico", "bi_instituicoes_apoio", "instituicao_apoio", "iap")
    dim_ref, ponte_ref = explode_dimension_with_bridge(df, "id_documento_logico", "referencias", "referencia", "ref")
    dim_cond, ponte_cond = explode_dimension_with_bridge(df, "id_documento_logico", "condicionantes_estudo_futuro", "condicionante", "con")
    dim_source_file, ponte_source_file = explode_dimension_with_bridge(df, "id_documento_logico", "source_files", "arquivo_origem", "src")

    dim_metodologia = (
        df[["bi_familia_do_metodo", "bi_tipo_estudo_futuro", "aplicou_estudo_futuro"]]
        .drop_duplicates()
        .reset_index(drop=True)
        .rename(columns={
            "bi_familia_do_metodo": "familia_do_metodo",
            "bi_tipo_estudo_futuro": "tipo_estudo_futuro",
        })
    )
    dim_metodologia["natureza_metodologia"] = dim_metodologia["familia_do_metodo"].apply(classify_method_nature)
    dim_metodologia["id_metodologia"] = [
        stable_hash_id("mdg", row.familia_do_metodo, row.tipo_estudo_futuro, row.aplicou_estudo_futuro)
        for row in dim_metodologia.itertuples(index=False)
    ]
    dim_metodologia = dim_metodologia[[
        "id_metodologia",
        "familia_do_metodo",
        "natureza_metodologia",
        "tipo_estudo_futuro",
        "aplicou_estudo_futuro",
    ]]

    dim_qualidade = build_quality_dimension(df)

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
        "dim_qualidade": dim_qualidade,
        "ponte_documento_tema": ponte_tema,
        "ponte_documento_metodo": ponte_metodo,
        "ponte_documento_instituicao_apoio": ponte_apoio,
        "ponte_documento_referencia": ponte_ref,
        "ponte_documento_condicionante": ponte_cond,
        "ponte_documento_arquivo_origem": ponte_source_file,
    }
