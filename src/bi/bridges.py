from __future__ import annotations

import pandas as pd
from src.shared.ids import stable_hash_id

def build_simple_dimension(df: pd.DataFrame, source_col: str, id_prefix: str, target_col: str | None = None) -> pd.DataFrame:
    target_col = target_col or source_col
    dim = (
        df[[source_col]]
        .dropna()
        .drop_duplicates()
        .rename(columns={source_col: target_col})
        .reset_index(drop=True)
    )
    dim[f"id_{target_col}"] = [
        stable_hash_id(id_prefix, value) for value in dim[target_col].tolist()
    ]
    cols = [f"id_{target_col}", target_col]
    return dim[cols]

def explode_dimension_with_bridge(
    df: pd.DataFrame,
    doc_id_col: str,
    list_col: str,
    value_col: str,
    id_prefix: str,
):
    exploded = df[[doc_id_col, list_col]].explode(list_col).dropna()
    exploded = exploded[exploded[list_col].astype(str).str.strip() != ""]
    exploded = exploded.rename(columns={list_col: value_col})

    dim = exploded[[value_col]].drop_duplicates().reset_index(drop=True)
    dim[f"id_{value_col}"] = [stable_hash_id(id_prefix, value) for value in dim[value_col].tolist()]

    bridge = exploded.merge(dim, on=value_col, how="left")[[doc_id_col, f"id_{value_col}"]].drop_duplicates()
    return dim[[f"id_{value_col}", value_col]], bridge
