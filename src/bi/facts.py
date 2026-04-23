from __future__ import annotations

import pandas as pd
from src.bi.dimensions import deserialize_list_columns
from src.shared.ids import stable_hash_id

def build_fact_inventory(df_raw: pd.DataFrame, dimensions: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = deserialize_list_columns(df_raw)

    dim_tempo = dimensions["dim_tempo"]
    dim_setor = dimensions["dim_setor"]
    dim_abrangencia = dimensions["dim_abrangencia"]
    dim_metodologia = dimensions["dim_metodologia"]

    fact = df.merge(
        dim_tempo,
        on=["ano_publicacao", "horizonte_temporal", "extensao_tempo"],
        how="left",
    )

    fact = fact.merge(
        dim_setor.rename(columns={"setor": "setor_norm", "id_setor": "id_dim_setor"}),
        on="setor_norm",
        how="left",
    )

    fact = fact.merge(
        dim_abrangencia.rename(columns={"abrangencia": "abrangencia_territorial_norm", "id_abrangencia": "id_dim_abrangencia"}),
        on="abrangencia_territorial_norm",
        how="left",
    )

    fact = fact.merge(
        dim_metodologia.rename(columns={"id_metodologia": "id_dim_metodologia"}),
        left_on=["familia_do_metodo_norm", "tipo_estudo_futuro", "aplicou_estudo_futuro"],
        right_on=["familia_do_metodo", "tipo_estudo_futuro", "aplicou_estudo_futuro"],
        how="left",
    )

    fact["id_fato_inventario"] = [
        stable_hash_id("fat", row.id_documento_logico, row.id_tempo, row.id_dim_setor, row.id_dim_abrangencia)
        for row in fact.itertuples(index=False)
    ]

    fact["qtd_temas"] = fact["temas_norm"].apply(len)
    fact["qtd_metodos"] = fact["metodos_estudo_futuro_norm"].apply(len)
    fact["qtd_referencias"] = fact["referencias"].apply(len)
    fact["possui_condicionantes"] = fact["condicionantes_estudo_futuro"].apply(lambda value: bool(value))

    return fact[[
        "id_fato_inventario",
        "id_documento_logico",
        "id_tempo",
        "id_dim_setor",
        "id_dim_abrangencia",
        "id_dim_metodologia",
        "ano_publicacao",
        "horizonte_temporal",
        "extensao_tempo",
        "aplicou_estudo_futuro",
        "qtd_arquivos_origem",
        "qtd_temas",
        "qtd_metodos",
        "qtd_referencias",
        "possui_condicionantes",
    ]]
