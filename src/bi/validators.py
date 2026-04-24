from __future__ import annotations

from typing import Any
import pandas as pd


def _key_check(name: str, df: pd.DataFrame) -> dict[str, Any]:
    first_col = df.columns[0]
    duplicated = int(df[first_col].duplicated().sum())
    nulls = int(df[first_col].isna().sum())
    return {
        "objeto": name,
        "teste": "chave_unica_nao_nula",
        "duplicados": duplicated,
        "nulos": nulls,
        "status": "ok" if duplicated == 0 and nulls == 0 else "erro",
    }


def _fact_fk_check(fact: pd.DataFrame, fk_col: str) -> dict[str, Any]:
    if fk_col not in fact.columns:
        return {"objeto": "fato_inventario", "teste": f"fk_{fk_col}", "nulos": -1, "status": "erro"}
    nulls = int(fact[fk_col].isna().sum())
    return {
        "objeto": "fato_inventario",
        "teste": f"fk_{fk_col}_nao_nula",
        "nulos": nulls,
        "status": "ok" if nulls == 0 else "warning",
    }


def run_bi_validations(dimensions: dict[str, pd.DataFrame], fact: pd.DataFrame) -> dict[str, Any]:
    report: dict[str, Any] = {"status": "ok", "checks": []}

    for name, df in dimensions.items():
        if name.startswith("dim_") and not df.empty:
            report["checks"].append(_key_check(name, df))

    duplicated_facts = int(fact["id_fato_inventario"].duplicated().sum()) if "id_fato_inventario" in fact.columns else -1
    report["checks"].append({
        "objeto": "fato_inventario",
        "teste": "chave_unica",
        "duplicados": duplicated_facts,
        "status": "ok" if duplicated_facts == 0 else "erro",
    })

    for fk_col in ["id_tempo", "id_dim_setor", "id_dim_abrangencia", "id_dim_metodologia", "id_qualidade"]:
        report["checks"].append(_fact_fk_check(fact, fk_col))

    statuses = [item["status"] for item in report["checks"]]
    if "erro" in statuses:
        report["status"] = "error"
    elif "warning" in statuses:
        report["status"] = "warning"

    return report
