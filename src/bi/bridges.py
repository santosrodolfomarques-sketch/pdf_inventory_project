from __future__ import annotations

import pandas as pd
from src.shared.ids import stable_hash_id


def add_surrogate_key(
    df: pd.DataFrame,
    sk_col: str,
    sort_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Adiciona uma chave substituta inteira estável, ordenando por colunas determinísticas."""
    df = df.copy()
    sort_cols = [col for col in (sort_cols or list(df.columns)) if col in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols, na_position="last").reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)
    if sk_col in df.columns:
        df = df.drop(columns=[sk_col])
    df.insert(0, sk_col, range(1, len(df) + 1))
    return df


def build_simple_dimension(
    df: pd.DataFrame,
    source_col: str,
    id_prefix: str,
    target_col: str | None = None,
    sk_col: str | None = None,
) -> pd.DataFrame:
    target_col = target_col or source_col
    sk_col = sk_col or f"sk_{target_col}"
    dim = (
        df[[source_col]]
        .dropna()
        .drop_duplicates()
        .rename(columns={source_col: target_col})
        .reset_index(drop=True)
    )
    dim = dim[dim[target_col].astype(str).str.strip() != ""]
    dim[f"id_{target_col}"] = [stable_hash_id(id_prefix, value) for value in dim[target_col].tolist()]
    dim = add_surrogate_key(dim[[f"id_{target_col}", target_col]], sk_col, [f"id_{target_col}"])
    return dim


def explode_dimension_with_bridge(
    df: pd.DataFrame,
    doc_id_col: str,
    list_col: str,
    value_col: str,
    id_prefix: str,
    doc_sk_map: pd.DataFrame | None = None,
    sk_col: str | None = None,
):
    sk_col = sk_col or f"sk_{value_col}"
    exploded = df[[doc_id_col, list_col]].explode(list_col).dropna()
    exploded = exploded[exploded[list_col].astype(str).str.strip() != ""]
    exploded = exploded.rename(columns={list_col: value_col})

    dim = exploded[[value_col]].drop_duplicates().reset_index(drop=True)
    dim[f"id_{value_col}"] = [stable_hash_id(id_prefix, value) for value in dim[value_col].tolist()]
    dim = add_surrogate_key(dim[[f"id_{value_col}", value_col]], sk_col, [f"id_{value_col}"])

    bridge_cols = [doc_id_col, sk_col, f"id_{value_col}"]
    bridge = exploded.merge(dim[[sk_col, f"id_{value_col}", value_col]], on=value_col, how="left")
    if doc_sk_map is not None and not doc_sk_map.empty:
        bridge = bridge.merge(doc_sk_map, on=doc_id_col, how="left")
        bridge_cols = ["sk_documento", doc_id_col, sk_col, f"id_{value_col}"]
    bridge = bridge[bridge_cols].drop_duplicates().reset_index(drop=True)
    return dim, bridge
