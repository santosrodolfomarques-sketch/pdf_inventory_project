from __future__ import annotations

import pandas as pd

from src.bi.dimensions import prepare_bi_dataframe
from src.bi.semantic_helpers import strip_accents_lower
from src.shared.ids import stable_hash_id


def _dedupe(df: pd.DataFrame, subset: list[str]) -> pd.DataFrame:
    existing = [col for col in subset if col in df.columns]
    if not existing:
        return df.drop_duplicates().reset_index(drop=True)
    return df.drop_duplicates(subset=existing, keep="first").reset_index(drop=True)


def _merge_dimension_sk(
    fact: pd.DataFrame,
    dim: pd.DataFrame,
    fact_col: str,
    dim_col: str,
    sk_col: str,
    hash_col: str | None = None,
) -> pd.DataFrame:
    cols = [sk_col, dim_col]
    if hash_col and hash_col in dim.columns:
        cols.append(hash_col)

    right = dim[cols].copy()
    right = _dedupe(right, [dim_col])
    return fact.merge(
        right.rename(columns={dim_col: fact_col}),
        on=fact_col,
        how="left",
        validate="many_to_one",
    )


def _merge_instituicao_responsavel(fact: pd.DataFrame, dimensions: dict[str, pd.DataFrame]) -> pd.DataFrame:
    dim_inst = dimensions.get("dim_instituicao_responsavel", pd.DataFrame())
    if dim_inst.empty or "sk_instituicao" not in dim_inst.columns or "instituicao" not in dim_inst.columns:
        fact["sk_instituicao"] = pd.NA
        return fact

    right = dim_inst[["sk_instituicao", "instituicao"]].copy()
    right["_inst_key"] = right["instituicao"].apply(strip_accents_lower)
    right = _dedupe(right, ["_inst_key"])

    fact["_inst_key"] = fact["bi_instituicao_responsavel"].apply(strip_accents_lower)
    fact = fact.merge(
        right[["sk_instituicao", "_inst_key"]],
        on="_inst_key",
        how="left",
        validate="many_to_one",
    )
    return fact.drop(columns=["_inst_key"], errors="ignore")


def build_fact_inventory(df_raw: pd.DataFrame, dimensions: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = prepare_bi_dataframe(df_raw)

    # A fato deve ter granularidade de 1 linha por documento lógico.
    if "id_documento_logico" in df.columns:
        df = df.drop_duplicates(subset=["id_documento_logico"], keep="first").reset_index(drop=True)

    dim_documento = dimensions["dim_documento"]
    dim_tempo = dimensions["dim_tempo"]
    dim_setor = dimensions["dim_setor"]
    dim_abrangencia = dimensions["dim_abrangencia"]
    dim_metodologia = dimensions["dim_metodologia"]
    dim_qualidade = dimensions.get("dim_qualidade", pd.DataFrame())

    fact = df.merge(
        _dedupe(
            dim_documento[["sk_documento", "id_documento_hash"]].rename(columns={"id_documento_hash": "id_documento_logico"}),
            ["id_documento_logico"],
        ),
        on="id_documento_logico",
        how="left",
        validate="many_to_one",
    )

    fact = fact.merge(
        _dedupe(
            dim_tempo,
            ["ano_publicacao", "horizonte_temporal", "extensao_tempo"],
        ),
        on=["ano_publicacao", "horizonte_temporal", "extensao_tempo"],
        how="left",
        validate="many_to_one",
    )

    fact = _merge_dimension_sk(fact, dim_setor, "bi_setor", "setor", "sk_setor", "id_setor")
    fact = _merge_dimension_sk(fact, dim_abrangencia, "bi_abrangencia", "abrangencia", "sk_abrangencia", "id_abrangencia")

    methodology_cols = [
        "sk_metodologia",
        "id_metodologia_hash",
        "familia_do_metodo",
        "tipo_estudo_futuro",
        "aplicou_estudo_futuro",
        "aplicou_estudo_futuro_status",
    ]
    existing_methodology_cols = [col for col in methodology_cols if col in dim_metodologia.columns]
    method_right = dim_metodologia[existing_methodology_cols].copy().rename(columns={
        "familia_do_metodo": "bi_familia_do_metodo",
        "tipo_estudo_futuro": "bi_tipo_estudo_futuro",
    })
    method_keys = [
        col for col in [
            "bi_familia_do_metodo",
            "bi_tipo_estudo_futuro",
            "aplicou_estudo_futuro",
            "aplicou_estudo_futuro_status",
        ]
        if col in fact.columns and col in method_right.columns
    ]
    method_right = _dedupe(method_right, method_keys)

    if method_keys:
        fact = fact.merge(method_right, on=method_keys, how="left", validate="many_to_one")
    else:
        fact["sk_metodologia"] = pd.NA
        fact["id_metodologia_hash"] = pd.NA

    if not dim_qualidade.empty:
        qual_cols = [
            "sk_documento",
            "sk_qualidade",
            "id_qualidade_hash",
            "score_qualidade",
            "nivel_qualidade",
            "flag_revisao_manual",
            "motivos_revisao",
        ]
        qual_right = _dedupe(dim_qualidade[[col for col in qual_cols if col in dim_qualidade.columns]], ["sk_documento"])
        fact = fact.merge(qual_right, on="sk_documento", how="left", validate="many_to_one")
    else:
        fact["sk_qualidade"] = pd.NA
        fact["id_qualidade_hash"] = pd.NA
        fact["score_qualidade"] = pd.NA
        fact["nivel_qualidade"] = pd.NA
        fact["flag_revisao_manual"] = pd.NA
        fact["motivos_revisao"] = pd.NA

    # Nova FK direta para instituição responsável.
    fact = _merge_instituicao_responsavel(fact, dimensions)

    fact["qtd_temas"] = fact["bi_temas"].apply(len)
    fact["qtd_metodos"] = fact["bi_metodos"].apply(len)
    fact["qtd_referencias"] = fact["referencias"].apply(len)
    fact["qtd_condicionantes"] = fact["condicionantes_estudo_futuro"].apply(len)
    fact["qtd_instituicoes_apoio"] = fact["bi_instituicoes_apoio"].apply(len)
    fact["possui_condicionantes"] = fact["qtd_condicionantes"] > 0
    fact["possui_metodo_identificado"] = fact["qtd_metodos"] > 0
    fact["possui_horizonte_temporal"] = fact["horizonte_temporal"].notna()
    fact["densidade_informacional"] = (
        fact["qtd_temas"] + fact["qtd_metodos"] + fact["qtd_referencias"] + fact["qtd_condicionantes"]
    )

    fact["id_fato_inventario_hash"] = [
        stable_hash_id(
            "fat",
            getattr(row, "id_documento_logico", None),
            getattr(row, "id_tempo_hash", None),
            getattr(row, "id_setor", None),
            getattr(row, "id_abrangencia", None),
            getattr(row, "id_metodologia_hash", None),
            getattr(row, "sk_instituicao", None),
        )
        for row in fact.itertuples(index=False)
    ]

    # Garante novamente 1 linha por documento depois dos merges.
    if "sk_documento" in fact.columns:
        fact = fact.drop_duplicates(subset=["sk_documento"], keep="first")

    fact = fact.sort_values(["sk_documento"], na_position="last").reset_index(drop=True)
    if "sk_fato_inventario" in fact.columns:
        fact = fact.drop(columns=["sk_fato_inventario"])
    fact.insert(0, "sk_fato_inventario", range(1, len(fact) + 1))

    cols = [
        "sk_fato_inventario",
        "id_fato_inventario_hash",
        "sk_documento",
        "id_documento_logico",
        "sk_tempo",
        "id_tempo_hash",
        "sk_setor",
        "id_setor",
        "sk_abrangencia",
        "id_abrangencia",
        "sk_instituicao",
        "sk_metodologia",
        "id_metodologia_hash",
        "sk_qualidade",
        "id_qualidade_hash",
        "ano_publicacao",
        "horizonte_temporal",
        "extensao_tempo",
        "aplicou_estudo_futuro",
        "aplicou_estudo_futuro_status",
        "qtd_arquivos_origem",
        "qtd_temas",
        "qtd_metodos",
        "qtd_referencias",
        "qtd_condicionantes",
        "qtd_instituicoes_apoio",
        "densidade_informacional",
        "possui_condicionantes",
        "possui_metodo_identificado",
        "possui_horizonte_temporal",
        "score_qualidade",
        "nivel_qualidade",
        "flag_revisao_manual",
        "motivos_revisao",
        "nome_documento",
        "nome_documento_norm",
        "nome_documento_curto",
        "tipo_documento",
        "tipo_documento_norm",
        "setor",
        "setor_norm",
        "abrangencia_territorial",
        "abrangencia_territorial_norm",
        "instituicao_responsavel",
        "instituicao_responsavel_norm",
        "tipo_estudo_futuro",
        "tipo_estudo_futuro_norm",
        "familia_do_metodo",
        "familia_do_metodo_norm",
        "source_file_name",
        "source_file_hash",
    ]
    return fact[[col for col in cols if col in fact.columns]]
