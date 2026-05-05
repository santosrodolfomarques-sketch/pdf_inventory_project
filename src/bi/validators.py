from __future__ import annotations

from typing import Any
import pandas as pd


def _key_check(name: str, df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"objeto": name, "teste": "dimensao_vazia", "status": "warning"}
    first_col = df.columns[0]
    duplicated = int(df[first_col].duplicated().sum())
    nulls = int(df[first_col].isna().sum())
    return {
        "objeto": name,
        "teste": f"{first_col}_unica_nao_nula",
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


def _bridge_fk_check(bridge_name: str, bridge: pd.DataFrame, sk_cols: list[str]) -> list[dict[str, Any]]:
    checks = []
    for col in sk_cols:
        if col in bridge.columns:
            nulls = int(bridge[col].isna().sum())
            checks.append({
                "objeto": bridge_name,
                "teste": f"{col}_nao_nula",
                "nulos": nulls,
                "status": "ok" if nulls == 0 else "warning",
            })
    return checks


def _column_presence_check(name: str, df: pd.DataFrame, required_cols: list[str], warning_only: bool = True) -> list[dict[str, Any]]:
    checks = []
    for col in required_cols:
        exists = col in df.columns
        checks.append({
            "objeto": name,
            "teste": f"coluna_{col}_existe",
            "status": "ok" if exists else ("warning" if warning_only else "erro"),
        })
    return checks


def run_bi_validations(dimensions: dict[str, pd.DataFrame], fact: pd.DataFrame) -> dict[str, Any]:
    report: dict[str, Any] = {"status": "ok", "checks": []}

    for name, df in dimensions.items():
        if name.startswith("dim_"):
            report["checks"].append(_key_check(name, df))

    duplicated_facts = int(fact["sk_fato_inventario"].duplicated().sum()) if "sk_fato_inventario" in fact.columns else -1
    report["checks"].append({
        "objeto": "fato_inventario",
        "teste": "sk_fato_inventario_unica",
        "duplicados": duplicated_facts,
        "status": "ok" if duplicated_facts == 0 else "erro",
    })

    for fk_col in ["sk_documento", "sk_tempo", "sk_setor", "sk_abrangencia", "sk_metodologia", "sk_qualidade"]:
        report["checks"].append(_fact_fk_check(fact, fk_col))

    for name, df in dimensions.items():
        if name.startswith("ponte_") and not df.empty:
            sk_cols = [col for col in df.columns if col.startswith("sk_")]
            report["checks"].extend(_bridge_fk_check(name, df, sk_cols))

    # Checagens semânticas importantes para o dashboard.
    if "dim_instituicao_responsavel" in dimensions:
        report["checks"].extend(_column_presence_check(
            "dim_instituicao_responsavel",
            dimensions["dim_instituicao_responsavel"],
            ["tipo_instituicao", "origem_instituicao", "nivel_governamental", "pais_ou_escopo", "confianca_enriquecimento"],
        ))
    if "dim_apoio" in dimensions:
        report["checks"].extend(_column_presence_check(
            "dim_apoio",
            dimensions["dim_apoio"],
            ["tipo_instituicao", "origem_instituicao", "nivel_governamental", "pais_ou_escopo", "confianca_enriquecimento"],
        ))
    if "dim_metodo" in dimensions:
        report["checks"].extend(_column_presence_check(
            "dim_metodo",
            dimensions["dim_metodo"],
            ["codigo_familia", "familia_metodo", "codigo_subfamilia", "subfamilia_metodo", "natureza_metodo", "funcao_primaria", "grau_prospectivo", "confianca_enriquecimento"],
        ))
    if "dim_condicionante" in dimensions:
        report["checks"].extend(_column_presence_check(
            "dim_condicionante",
            dimensions["dim_condicionante"],
            ["condicionante_normalizado", "tipo_prospectivo", "categoria_steep", "cluster", "macrocondicionante", "horizonte_implicado", "direcionalidade", "eh_condicionante_prospectivo", "confianca_enriquecimento"],
        ))

    if "dim_source_file" in dimensions:
        empty_source = dimensions["dim_source_file"].empty
        report["checks"].append({
            "objeto": "dim_source_file",
            "teste": "rastreabilidade_arquivo_origem",
            "status": "warning" if empty_source else "ok",
        })

    statuses = [item["status"] for item in report["checks"]]
    if "erro" in statuses:
        report["status"] = "error"
    elif "warning" in statuses:
        report["status"] = "warning"

    return report
