from __future__ import annotations

import pandas as pd

from src.bi.dimensions import prepare_bi_dataframe
from src.shared.ids import stable_hash_id


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
    merged = fact.merge(dim[cols].rename(columns={dim_col: fact_col}), on=fact_col, how="left")
    return merged


def build_fact_inventory(df_raw: pd.DataFrame, dimensions: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = prepare_bi_dataframe(df_raw)

    dim_documento = dimensions["dim_documento"]
    dim_tempo = dimensions["dim_tempo"]
    dim_setor = dimensions["dim_setor"]
    dim_abrangencia = dimensions["dim_abrangencia"]
    dim_metodologia = dimensions["dim_metodologia"]
    dim_qualidade = dimensions.get("dim_qualidade", pd.DataFrame())

    fact = df.merge(
        dim_documento[["sk_documento", "id_documento_hash"]].rename(columns={"id_documento_hash": "id_documento_logico"}),
        on="id_documento_logico",
        how="left",
    )

    fact = fact.merge(
        dim_tempo[["sk_tempo", "id_tempo_hash"]],
        on="id_tempo_hash",
        how="left",
    )

    fact = _merge_dimension_sk(fact, dim_setor, "bi_setor", "setor", "sk_setor", "id_setor")
    fact = _merge_dimension_sk(fact, dim_abrangencia, "bi_abrangencia", "abrangencia", "sk_abrangencia", "id_abrangencia")

    fact = fact.merge(
        dim_metodologia[[
            "sk_metodologia",
            "id_metodologia_hash",
            "familia_do_metodo",
            "tipo_estudo_futuro",
            "aplicou_estudo_futuro",
        ]].rename(
            columns={
                "familia_do_metodo": "bi_familia_do_metodo",
                "tipo_estudo_futuro": "bi_tipo_estudo_futuro",
            }
        ),
        on=["bi_familia_do_metodo", "bi_tipo_estudo_futuro", "aplicou_estudo_futuro"],
        how="left",
    )

    if not dim_qualidade.empty:
        fact = fact.merge(
            dim_qualidade[[
                "sk_documento",
                "sk_qualidade",
                "id_qualidade_hash",
                "score_qualidade",
                "nivel_qualidade",
                "flag_revisao_manual",
            ]].rename(columns={"flag_revisao_manual": "flag_revisao_manual_qualidade"}),
            on="sk_documento",
            how="left",
        )
        if "flag_revisao_manual" in fact.columns:
            fact["flag_revisao_manual"] = fact["flag_revisao_manual_qualidade"].combine_first(
                fact["flag_revisao_manual"]
            )
        else:
            fact["flag_revisao_manual"] = fact["flag_revisao_manual_qualidade"]
    else:
        fact["sk_qualidade"] = pd.NA
        fact["id_qualidade_hash"] = pd.NA
        fact["score_qualidade"] = pd.NA
        fact["nivel_qualidade"] = pd.NA
        fact["flag_revisao_manual"] = pd.NA

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
            row.id_documento_logico,
            row.get("id_tempo_hash") if hasattr(row, "get") else getattr(row, "id_tempo_hash", None),
            getattr(row, "id_setor", None),
            getattr(row, "id_abrangencia", None),
            getattr(row, "id_metodologia_hash", None),
        )
        for row in fact.itertuples(index=False)
    ]

    fact = fact.sort_values(["sk_documento"], na_position="last").reset_index(drop=True)
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
        "sk_metodologia",
        "id_metodologia_hash",
        "sk_qualidade",
        "id_qualidade_hash",
        "ano_publicacao",
        "horizonte_temporal",
        "extensao_tempo",
        "aplicou_estudo_futuro",
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
    ]
    return fact[[col for col in cols if col in fact.columns]]
