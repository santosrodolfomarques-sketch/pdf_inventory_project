from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.shared.config import Settings
from src.shared.utils import remove_accents_lower, to_json_string


SCALAR_FIELDS = {
    "setor": ("setor", "setor_norm"),
    "tipo_documento": ("tipo_documento", "tipo_documento_norm"),
    "abrangencia_territorial": ("abrangencia_territorial", "abrangencia_territorial_norm"),
    "tipo_estudo_futuro": ("tipo_estudo_futuro", "tipo_estudo_futuro_norm"),
    "familia_do_metodo": ("familia_do_metodo_norm", "familia_do_metodo_norm"),
    "instituicoes": ("instituicao_responsavel", "instituicao_responsavel_norm"),
}

LIST_FIELDS = {
    "temas": ("temas", "temas_norm"),
    "metodos": ("metodos_estudo_futuro", "metodos_estudo_futuro_norm"),
    "instituicoes": ("instituicoes_apoio", "instituicoes_apoio_norm"),
}


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def _load_json_list(value: Any) -> list[Any]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return value
    text = str(value).strip()
    if not text:
        return []
    try:
        loaded = json.loads(text)
        return loaded if isinstance(loaded, list) else [loaded]
    except Exception:
        return [text]


def _load_dictionary(path: Path, apply_only: bool = True) -> dict[str, dict[str, Any]]:
    df = _read_csv(path)
    if df.empty:
        return {}
    if apply_only and "aplicar_automaticamente" in df.columns:
        df = df[df["aplicar_automaticamente"].astype(str).str.lower().isin(["true", "1", "sim", "yes"])]

    mapping: dict[str, dict[str, Any]] = {}
    for _, row in df.iterrows():
        key = row.get("valor_original_limpo") or remove_accents_lower(row.get("valor_original"))
        if not key:
            continue
        mapping[str(key)] = {
            "valor_normalizado": row.get("valor_normalizado"),
            "categoria": row.get("categoria"),
            "confianca": row.get("confianca"),
            "acao_recomendada": row.get("acao_recomendada"),
        }
    return mapping


def _map_scalar(value: Any, mapping: dict[str, dict[str, Any]]) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return value
    key = remove_accents_lower(value)
    item = mapping.get(key)
    if not item:
        return value
    mapped = item.get("valor_normalizado")
    return mapped if mapped is not None and str(mapped).strip() else value


def _map_list(value: Any, mapping: dict[str, dict[str, Any]]) -> list[Any]:
    values = _load_json_list(value)
    output: list[Any] = []
    seen: set[str] = set()
    for item in values:
        mapped = _map_scalar(item, mapping)
        marker = remove_accents_lower(mapped)
        if marker in seen:
            continue
        seen.add(marker)
        output.append(mapped)
    return output


def _apply_to_dataframe(df: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    if df.empty:
        return df

    result = df.copy()

    for target, (source_col, dest_col) in SCALAR_FIELDS.items():
        dict_path = settings.ai_dictionary_dir / f"dicionario_{target}.csv"
        mapping = _load_dictionary(dict_path, apply_only=True)
        if not mapping or source_col not in result.columns:
            continue
        result[dest_col] = result[source_col].apply(lambda value: _map_scalar(value, mapping))

        # Campo auxiliar de categoria, quando houver.
        category_col = f"{dest_col}_categoria"
        result[category_col] = result[source_col].apply(
            lambda value: mapping.get(remove_accents_lower(value), {}).get("categoria") if value is not None else None
        )

    for target, (source_col, dest_col) in LIST_FIELDS.items():
        dict_path = settings.ai_dictionary_dir / f"dicionario_{target}.csv"
        mapping = _load_dictionary(dict_path, apply_only=True)
        if not mapping or source_col not in result.columns:
            continue
        result[dest_col] = result[source_col].apply(lambda value: to_json_string(_map_list(value, mapping)))

    return result


def apply_ai_dictionaries(settings: Settings, logger: Any) -> dict[str, Any]:
    settings.ai_applied_dir.mkdir(parents=True, exist_ok=True)

    sources = {
        "documentos_tratados.csv": settings.transformed_base_dir / "documentos_tratados.csv",
        "documentos_consolidados.csv": settings.transformed_base_dir / "documentos_consolidados.csv",
    }

    outputs: dict[str, str] = {}
    for filename, path in sources.items():
        if not path.exists():
            logger.info(f"Aplicação de dicionários IA: arquivo não encontrado: {path}")
            continue
        df = pd.read_csv(path, encoding="utf-8-sig")
        normalized_df = _apply_to_dataframe(df, settings)
        out_path = settings.ai_applied_dir / filename.replace(".csv", "_normalizado_ia.csv")
        normalized_df.to_csv(out_path, index=False, encoding="utf-8-sig")
        outputs[filename] = str(out_path)

    logger.info("Aplicação dos dicionários IA concluída.")
    return {"status": "ok", "outputs": outputs}
