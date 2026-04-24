from __future__ import annotations

import pandas as pd

from src.bi.dimensions import prepare_bi_dataframe
from src.shared.ids import stable_hash_id


def _merge_dimension_id(
    fact: pd.DataFrame,
    dim: pd.DataFrame,
    fact_col: str,
    dim_col: str,
    dim_id_col: str,
    output_id_col: str,
) -> pd.DataFrame:
    return fact.merge(
        dim[[dim_id_col, dim_col]].rename(columns={dim_col: fact_col, dim_id_col: output_id_col}),
        on=fact_col,
        how="left",
    )


def build_fact_inventory(df_raw: pd.DataFrame, dimensions: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = prepare_bi_dataframe(df_raw)

    dim_tempo = dimensions["dim_tempo"]
    dim_setor = dimensions["dim_setor"]
    dim_abrangencia = dimensions["dim_abrangencia"]
    dim_metodologia = dimensions["dim_metodologia"]
    dim_qualidade = dimensions.get("dim_qualidade", pd.DataFrame())

    fact = df.merge(
        dim_tempo,
        on=["ano_publicacao", "horizonte_temporal", "extensao_tempo"],
        how="left",
    )

    fact = _merge_dimension_id(fact, dim_setor, "bi_setor", "setor", "id_setor", "id_dim_setor")
    fact = _merge_dimension_id(fact, dim_abrangencia, "bi_abrangencia", "abrangencia", "id_abrangencia", "id_dim_abrangencia")

    fact = fact.merge(
        dim_metodologia[["id_metodologia", "familia_do_metodo", "tipo_estudo_futuro", "aplicou_estudo_futuro"]].rename(
            columns={
                "id_metodologia": "id_dim_metodologia",
                "familia_do_metodo": "bi_familia_do_metodo",
                "tipo_estudo_futuro": "bi_tipo_estudo_futuro",
            }
        ),
        on=["bi_familia_do_metodo", "bi_tipo_estudo_futuro", "aplicou_estudo_futuro"],
        how="left",
    )

    if not dim_qualidade.empty:
        fact = fact.merge(
            dim_qualidade[["id_documento_logico", "id_qualidade", "score_qualidade", "nivel_qualidade", "flag_revisao_manual"]],
            on="id_documento_logico",
            how="left",
        )
    else:
        fact["id_qualidade"] = None
        fact["score_qualidade"] = None
        fact["nivel_qualidade"] = None
        fact["flag_revisao_manual"] = None

    fact["id_fato_inventario"] = [
        stable_hash_id(
            "fat",
            row.id_documento_logico,
            row.id_tempo,
            row.id_dim_setor,
            row.id_dim_abrangencia,
            row.id_dim_metodologia,
        )
        for row in fact.itertuples(index=False)
    ]

    fact["qtd_temas"] = fact["bi_temas"].apply(len)
    fact["qtd_metodos"] = fact["bi_metodos"].apply(len)
    fact["qtd_referencias"] = fact["referencias"].apply(len)
    fact["qtd_condicionantes"] = fact["condicionantes_estudo_futuro"].apply(len)
    fact["possui_condicionantes"] = fact["qtd_condicionantes"] > 0
    fact["possui_metodo_identificado"] = fact["qtd_metodos"] > 0
    fact["possui_horizonte_temporal"] = fact["horizonte_temporal"].notna()

    cols = [
        "id_fato_inventario",
        "id_documento_logico",
        "id_tempo",
        "id_dim_setor",
        "id_dim_abrangencia",
        "id_dim_metodologia",
        "id_qualidade",
        "ano_publicacao",
        "horizonte_temporal",
        "extensao_tempo",
        "aplicou_estudo_futuro",
        "qtd_arquivos_origem",
        "qtd_temas",
        "qtd_metodos",
        "qtd_referencias",
        "qtd_condicionantes",
        "possui_condicionantes",
        "possui_metodo_identificado",
        "possui_horizonte_temporal",
        "score_qualidade",
        "nivel_qualidade",
        "flag_revisao_manual",
    ]
    return fact[[col for col in cols if col in fact.columns]]
