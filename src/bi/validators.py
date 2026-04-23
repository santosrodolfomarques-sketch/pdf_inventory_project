from __future__ import annotations

from typing import Any
import pandas as pd

def run_bi_validations(dimensions: dict[str, pd.DataFrame], fact: pd.DataFrame) -> dict[str, Any]:
    report: dict[str, Any] = {"status": "ok", "checks": []}

    for name, df in dimensions.items():
        if name.startswith("dim_"):
            first_col = df.columns[0]
            duplicated = int(df[first_col].duplicated().sum())
            report["checks"].append({
                "objeto": name,
                "teste": "chave_unica",
                "duplicados": duplicated,
                "status": "ok" if duplicated == 0 else "erro",
            })

    duplicated_facts = int(fact["id_fato_inventario"].duplicated().sum()) if "id_fato_inventario" in fact.columns else -1
    report["checks"].append({
        "objeto": "fato_inventario",
        "teste": "chave_unica",
        "duplicados": duplicated_facts,
        "status": "ok" if duplicated_facts == 0 else "erro",
    })

    if any(item["status"] == "erro" for item in report["checks"]):
        report["status"] = "warning"

    return report
