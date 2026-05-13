from __future__ import annotations

import pandas as pd

from src.bi.bridges import add_surrogate_key, build_simple_dimension, explode_dimension_with_bridge
from src.bi.semantic_helpers import (
    choose_list,
    choose_scalar,
    classify_macrotema,
    classify_method_family,
    classify_method_nature,
    classify_subtema,
    coalesce_text,
    fill_text,
    quality_level,
    safe_parse_list,
    to_bool_or_false,
    strip_accents_lower,
)
from src.shared.ids import stable_hash_id

LIST_COLUMNS = [
    "temas",
    "temas_norm",
    "metodos_estudo_futuro",
    "metodos_estudo_futuro_norm",
    "instituicoes_apoio",
    "instituicoes_apoio_norm",
    "referencias",
    "condicionantes_estudo_futuro",
    "source_files",
    "setor",
    "abrangencia_territorial",
]


def load_review_dictionary(settings, filename: str) -> pd.DataFrame | None:
    if settings is None:
        return None
    path = settings.transformed_base_dir.parents[1] / "04_review" / "dicionarios_manuais" / filename
    if not path.exists():
        return None
    df = pd.read_csv(path, encoding="utf-8-sig")
    if df.empty:
        return None
        
    norm_col = None
    if "valor_normalizado" in df.columns:
        norm_col = "valor_normalizado"
    elif "tema_normalizado" in df.columns:
        norm_col = "tema_normalizado"
        
    if not norm_col:
        return None
        
    df = df.dropna(subset=[norm_col]).copy()
    df["_merge_key"] = df[norm_col].apply(strip_accents_lower)
    df = df.drop_duplicates(subset=["_merge_key"], keep="last")
    df["valor_original"] = df[norm_col]
    return df

def load_enrichment_dictionary(settings, filename: str) -> pd.DataFrame | None:
    if settings is None:
        return None
    path = settings.enrichment_dir / filename
    if not path.exists():
        return None
    df = pd.read_csv(path, encoding="utf-8-sig")
    if df.empty or "valor_original" not in df.columns:
        return None
    df = df.dropna(subset=["valor_original"]).copy()
    df["_merge_key"] = df["valor_original"].apply(strip_accents_lower)
    df = df.drop_duplicates(subset=["_merge_key"], keep="last")
    return df

def load_merged_dictionary(settings, review_filename: str, enriched_filename: str) -> pd.DataFrame | None:
    df_review = load_review_dictionary(settings, review_filename)
    df_enriched = load_enrichment_dictionary(settings, enriched_filename)

    if df_review is None and df_enriched is None:
        return None
    if df_review is None:
        return df_enriched
    if df_enriched is None:
        return df_review

    df_merged = df_review.merge(df_enriched, on="_merge_key", how="outer", suffixes=("_man", "_ia"))
    
    for col in df_enriched.columns:
        if col == "_merge_key":
            continue
        if col in df_review.columns:
            df_merged[col] = df_merged[col + "_man"].fillna(df_merged[col + "_ia"])
            df_merged = df_merged.drop(columns=[col + "_man", col + "_ia"])
            
    return df_merged

def prepare_bi_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Prepara a base para BI priorizando colunas normalizadas e preenchendo vazios críticos."""
    df = df_raw.copy()

    for column in LIST_COLUMNS:
        if column in df.columns:
            df[column] = df[column].apply(safe_parse_list)

    # Rastreabilidade: se source_files não existir ou vier vazio, usa source_file_name.
    if "source_files" not in df.columns:
        df["source_files"] = [[] for _ in range(len(df))]
    if "source_file_name" in df.columns:
        df["source_files"] = [
            files if files else safe_parse_list(source)
            for files, source in zip(df["source_files"].apply(safe_parse_list), df["source_file_name"])
        ]

    df["bi_nome_documento"] = choose_scalar(df, "nome_documento", "Não informado")
    if "nome_documento_curto" in df.columns:
        df["bi_nome_documento_curto"] = df["nome_documento_curto"].apply(lambda v: fill_text(v, "Não informado"))
    else:
        df["bi_nome_documento_curto"] = df["bi_nome_documento"].apply(
            lambda v: (str(v)[:77].rstrip() + "...") if len(str(v)) > 80 else str(v)
        )
    df["bi_tipo_documento"] = choose_scalar(df, "tipo_documento", "Não informado")
    df["bi_instituicao_responsavel"] = choose_scalar(df, "instituicao_responsavel", "Não informado")
    df["bi_tipo_estudo_futuro"] = choose_scalar(df, "tipo_estudo_futuro", "Não informado")
    df["bi_familia_do_metodo"] = choose_scalar(df, "familia_do_metodo", "Não classificado")

    df["bi_setores"] = choose_list(df, "setor")
    df["bi_abrangencias"] = choose_list(df, "abrangencia_territorial")
    df["bi_temas"] = choose_list(df, "temas")
    df["bi_metodos"] = choose_list(df, "metodos_estudo_futuro")
    df["bi_instituicoes_apoio"] = choose_list(df, "instituicoes_apoio")

    for col in ["referencias", "condicionantes_estudo_futuro", "source_files"]:
        if col not in df.columns:
            df[col] = [[] for _ in range(len(df))]
        df[col] = df[col].apply(safe_parse_list)

    if "qtd_arquivos_origem" not in df.columns:
        df["qtd_arquivos_origem"] = df["source_files"].apply(lambda x: len(x) if isinstance(x, list) else 0)
    else:
        df["qtd_arquivos_origem"] = df["qtd_arquivos_origem"].fillna(df["source_files"].apply(len)).astype(int)

    # Booleano padronizado para BI.
    if "aplicou_estudo_futuro" not in df.columns:
        df["aplicou_estudo_futuro"] = False
    df["aplicou_estudo_futuro"] = df["aplicou_estudo_futuro"].apply(to_bool_or_false)
    df["aplicou_estudo_futuro_status"] = df["aplicou_estudo_futuro"].map({True: "Sim", False: "Não"})

    return df


# Compatibilidade com módulos antigos.
def deserialize_list_columns(df: pd.DataFrame) -> pd.DataFrame:
    return prepare_bi_dataframe(df)


def build_document_dimension(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "id_documento_logico",
        "bi_nome_documento",
        "bi_nome_documento_curto",
        "sigla_ou_abreviacao",
        "bi_tipo_documento",
        "bi_instituicao_responsavel",
        "qtd_arquivos_origem",
    ]
    existing = [col for col in cols if col in df.columns]
    dim = df[existing].drop_duplicates().rename(columns={
        "id_documento_logico": "id_documento_hash",
        "bi_nome_documento": "nome_documento",
        "bi_nome_documento_curto": "nome_documento_curto",
        "bi_tipo_documento": "tipo_documento",
        "bi_instituicao_responsavel": "instituicao_responsavel",
    })
    for col in ["nome_documento", "nome_documento_curto", "tipo_documento", "instituicao_responsavel", "sigla_ou_abreviacao"]:
        if col in dim.columns:
            dim[col] = dim[col].apply(lambda v: fill_text(v, "Não informado"))
    dim = add_surrogate_key(dim, "sk_documento", ["id_documento_hash"])
    return dim.reset_index(drop=True)


def build_time_dimension(df: pd.DataFrame) -> pd.DataFrame:
    base_cols = ["ano_publicacao", "horizonte_temporal", "extensao_tempo"]
    for col in base_cols:
        if col not in df.columns:
            df[col] = pd.NA
    dim = (
        df[base_cols]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    if dim.empty:
        dim = pd.DataFrame([{"ano_publicacao": pd.NA, "horizonte_temporal": pd.NA, "extensao_tempo": pd.NA}])
    dim["id_tempo_hash"] = [
        stable_hash_id("tmp", row.ano_publicacao, row.horizonte_temporal, row.extensao_tempo)
        for row in dim.itertuples(index=False)
    ]
    dim = add_surrogate_key(
        dim[["id_tempo_hash", "ano_publicacao", "horizonte_temporal", "extensao_tempo"]],
        "sk_tempo",
        ["id_tempo_hash"],
    )
    return dim


def _fill_enrichment_defaults(df: pd.DataFrame, institutional: bool = False, conditional: bool = False) -> pd.DataFrame:
    df = df.copy()
    if institutional:
        defaults = {
            "tipo_instituicao": "Não classificado",
            "origem_instituicao": "Não classificado",
            "nivel_governamental": "Não informado",
            "pais_ou_escopo": "Não informado",
            "acao_recomendada": "revisar_manual",
            "fonte_classificacao": "não informado",
            "qualidade_classificacao": "Não informada",
            "confianca_enriquecimento": "não informado",
            "justificativa": "",
        }
    elif conditional:
        defaults = {
            "condicionante_normalizado": "Não classificado",
            "tipo_prospectivo": "Não classificado",
            "categoria_steep": "Não classificado",
            "categoria": "Não classificado",
            "cluster": "Não classificado",
            "macrocondicionante": "Não classificado",
            "horizonte_implicado": "Não informado",
            "direcionalidade": "Não informado",
            "eh_condicionante_prospectivo": "Revisar",
            "confianca_enriquecimento": "não informado",
            "acao_recomendada": "revisar_manual",
            "justificativa": "",
        }
    else:
        defaults = {}
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
        else:
            df[col] = df[col].apply(lambda v: fill_text(v, default))
    return df


def apply_institution_enrichment(
    dim: pd.DataFrame,
    enrichment: pd.DataFrame | None,
    institution_column: str,
) -> pd.DataFrame:
    if dim.empty:
        return _fill_enrichment_defaults(dim, institutional=True)
    if enrichment is None or "_merge_key" not in enrichment.columns:
        return _fill_enrichment_defaults(dim, institutional=True)

    left = dim.copy()
    left["_merge_key"] = left[institution_column].apply(strip_accents_lower)
    enriched = left.merge(
        enrichment,
        on="_merge_key",
        how="left",
        suffixes=("", "_dict"),
    ).drop(columns=["_merge_key", "valor_original"], errors="ignore")

    enriched = enriched.rename(columns={"confianca": "confianca_enriquecimento"})
    return _fill_enrichment_defaults(enriched, institutional=True)

def apply_condition_enrichment(
    dim: pd.DataFrame,
    enrichment: pd.DataFrame | None,
) -> pd.DataFrame:
    if dim.empty:
        return _fill_enrichment_defaults(dim, conditional=True)
    if enrichment is None or "_merge_key" not in enrichment.columns:
        return _fill_enrichment_defaults(dim, conditional=True)

    left = dim.copy()
    left["_merge_key"] = left["condicionante"].apply(strip_accents_lower)
    enriched = left.merge(
        enrichment,
        on="_merge_key",
        how="left",
        suffixes=("", "_dict"),
    ).drop(columns=["_merge_key", "valor_original"], errors="ignore")

    enriched = enriched.rename(columns={"confianca": "confianca_enriquecimento"})
    return _fill_enrichment_defaults(enriched, conditional=True)


def _fill_method_enrichment_defaults(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    defaults = {
        "metodo_normalizado": None,
        "codigo_familia": "Não classificado",
        "familia_metodo": "Não classificado",
        "codigo_subfamilia": "Não classificado",
        "subfamilia_metodo": "Não classificado",
        "natureza_metodo": "Não classificado",
        "funcao_primaria": "Não classificado",
        "grau_prospectivo": "Não classificado",
        "confianca_enriquecimento": "não informado",
        "acao_recomendada": "revisar_manual",
        "justificativa_metodo": "",
        "fonte_classificacao": "não informado",
        "qualidade_classificacao": "Não informada",
    }
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
        elif default is not None:
            df[col] = df[col].apply(lambda v: fill_text(v, default))

    if "metodo_normalizado" in df.columns and "metodo" in df.columns:
        df["metodo_normalizado"] = df.apply(
            lambda row: fill_text(row.get("metodo_normalizado"), fill_text(row.get("metodo"), "Não informado")),
            axis=1,
        )
    return df


def apply_method_taxonomy_enrichment(
    dim: pd.DataFrame,
    enrichment: pd.DataFrame | None,
) -> pd.DataFrame:
    if dim.empty:
        return _fill_method_enrichment_defaults(dim)
    if enrichment is None or "valor_original" not in enrichment.columns:
        base = dim.copy()
        if "familia_metodo" not in base.columns and "familia_do_metodo" in base.columns:
            base["familia_metodo"] = base["familia_do_metodo"]
        return _fill_method_enrichment_defaults(base)

    dictionary = enrichment.copy()
    rename_map = {
        "valor_normalizado": "metodo_normalizado",
        "natureza_metodo": "natureza_metodo_taxonomia",
        "confianca": "confianca_enriquecimento",
        "justificativa": "justificativa_metodo",
    }
    dictionary = dictionary.rename(columns=rename_map)

    dictionary["_merge_key"] = dictionary["valor_original"].apply(strip_accents_lower)
    dictionary = dictionary.drop_duplicates(subset=["_merge_key"], keep="last")
    left = dim.copy()
    left["_merge_key"] = left["metodo"].apply(strip_accents_lower)
    enriched = left.merge(
        dictionary,
        on="_merge_key",
        how="left",
        suffixes=("", "_dict"),
    ).drop(columns=["_merge_key", "valor_original"], errors="ignore")

    if "familia_metodo" not in enriched.columns:
        enriched["familia_metodo"] = enriched.get("familia_do_metodo")
    else:
        enriched["familia_metodo"] = enriched.apply(
            lambda row: fill_text(row.get("familia_metodo"), fill_text(row.get("familia_do_metodo"), "Não classificado")),
            axis=1,
        )

    if "natureza_metodo_taxonomia" in enriched.columns:
        enriched["natureza_metodo"] = enriched.apply(
            lambda row: fill_text(row.get("natureza_metodo_taxonomia"), fill_text(row.get("natureza_metodo"), "Não classificado")),
            axis=1,
        )
        enriched = enriched.drop(columns=["natureza_metodo_taxonomia"], errors="ignore")

    return _fill_method_enrichment_defaults(enriched)

def build_theme_dimension_and_bridge(
    df: pd.DataFrame,
    doc_sk_map: pd.DataFrame,
    theme_dict: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = df[["id_documento_logico", "bi_temas"]].explode("bi_temas").dropna()
    base = base[base["bi_temas"].astype(str).str.strip() != ""]
    base = base.rename(columns={"bi_temas": "tema"})

    dim = base[["tema"]].drop_duplicates().reset_index(drop=True)
    
    if theme_dict is not None and "_merge_key" in theme_dict.columns:
        left = dim.copy()
        left["_merge_key"] = left["tema"].apply(strip_accents_lower)
        enriched = left.merge(
            theme_dict,
            on="_merge_key",
            how="left",
            suffixes=("", "_dict"),
        )
        enriched["macrotema"] = enriched.apply(lambda row: fill_text(row.get("macrotema"), classify_macrotema(row["tema"])), axis=1)
        enriched["subtema"] = enriched.apply(lambda row: fill_text(row.get("subtema"), classify_subtema(row["tema"])), axis=1)
        dim = enriched
    else:
        dim["macrotema"] = dim["tema"].apply(classify_macrotema)
        dim["subtema"] = dim["tema"].apply(classify_subtema)
        
    dim["id_tema_hash"] = [stable_hash_id("tem", row.tema) for row in dim.itertuples(index=False)]
    dim = add_surrogate_key(dim[["id_tema_hash", "tema", "macrotema", "subtema"]], "sk_tema", ["id_tema_hash"])

    ponte = base.merge(dim[["sk_tema", "id_tema_hash", "tema"]], on="tema", how="left")
    ponte = ponte.merge(doc_sk_map, on="id_documento_logico", how="left")
    ponte = ponte[["sk_documento", "id_documento_logico", "sk_tema", "id_tema_hash"]].drop_duplicates().reset_index(drop=True)
    return dim, ponte


def build_method_dimension_and_bridge(
    df: pd.DataFrame,
    doc_sk_map: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = df[["id_documento_logico", "bi_metodos", "bi_familia_do_metodo"]].explode("bi_metodos").dropna()
    base = base[base["bi_metodos"].astype(str).str.strip() != ""]
    base = base.rename(columns={"bi_metodos": "metodo"})

    dim = base[["metodo", "bi_familia_do_metodo"]].drop_duplicates().reset_index(drop=True)
    dim["familia_do_metodo"] = dim.apply(lambda row: classify_method_family(row["metodo"], row.get("bi_familia_do_metodo")), axis=1)
    dim["natureza_metodo"] = dim.apply(lambda row: classify_method_nature(row["familia_do_metodo"], row["metodo"]), axis=1)
    dim["id_metodo_hash"] = [stable_hash_id("met", row.metodo, row.familia_do_metodo) for row in dim.itertuples(index=False)]
    dim = add_surrogate_key(dim[["id_metodo_hash", "metodo", "familia_do_metodo", "natureza_metodo"]], "sk_metodo", ["id_metodo_hash"])

    ponte = base.merge(dim[["sk_metodo", "id_metodo_hash", "metodo"]], on="metodo", how="left")
    ponte = ponte.merge(doc_sk_map, on="id_documento_logico", how="left")
    ponte = ponte[["sk_documento", "id_documento_logico", "sk_metodo", "id_metodo_hash"]].drop_duplicates().reset_index(drop=True)
    return dim, ponte


def build_quality_dimension(df: pd.DataFrame, doc_sk_map: pd.DataFrame) -> pd.DataFrame:
    quality_rows = []
    for row in df.itertuples(index=False):
        qtd_temas = len(getattr(row, "bi_temas", []) or [])
        qtd_metodos = len(getattr(row, "bi_metodos", []) or [])
        qtd_referencias = len(getattr(row, "referencias", []) or [])
        possui_nome = bool(coalesce_text(getattr(row, "bi_nome_documento", None)))
        possui_ano = pd.notna(getattr(row, "ano_publicacao", None))
        possui_horizonte = pd.notna(getattr(row, "horizonte_temporal", None))
        possui_setor = len(getattr(row, "bi_setores", []) or []) > 0
        possui_abrangencia = len(getattr(row, "bi_abrangencias", []) or []) > 0
        aplicou_estudo = bool(getattr(row, "aplicou_estudo_futuro", False))

        score = 0.0
        score += 0.15 if possui_nome else 0
        score += 0.12 if possui_ano else 0
        score += 0.10 if possui_horizonte else 0
        score += 0.10 if possui_setor else 0
        score += 0.08 if possui_abrangencia else 0
        score += 0.15 if qtd_temas > 0 else 0
        score += 0.15 if qtd_referencias > 0 else 0
        score += 0.15 if (not aplicou_estudo or qtd_metodos > 0) else 0
        score = min(round(score, 3), 1.0)

        motivos = []
        if not possui_nome:
            motivos.append("nome_documento_ausente")
        if not possui_ano:
            motivos.append("ano_publicacao_ausente")
        if aplicou_estudo and qtd_metodos == 0:
            motivos.append("estudo_futuro_sem_metodo")
        if not possui_setor:
            motivos.append("setor_nao_informado")
        if not possui_abrangencia:
            motivos.append("abrangencia_nao_informada")

        flag_revisao_manual = bool(getattr(row, "flag_revisao_manual", False)) or bool(motivos)
        id_documento = getattr(row, "id_documento_logico")
        quality_rows.append({
            "id_documento_logico": id_documento,
            "id_qualidade_hash": stable_hash_id("qlt", id_documento, score, "|".join(motivos)),
            "score_qualidade": score,
            "nivel_qualidade": quality_level(score),
            "flag_revisao_manual": flag_revisao_manual,
            "motivos_revisao": "; ".join(motivos) if motivos else "",
        })

    dim = pd.DataFrame(quality_rows).drop_duplicates().reset_index(drop=True)
    dim = dim.merge(doc_sk_map, on="id_documento_logico", how="left")
    dim = add_surrogate_key(dim, "sk_qualidade", ["id_qualidade_hash"])
    return dim[[
        "sk_qualidade",
        "id_qualidade_hash",
        "sk_documento",
        "id_documento_logico",
        "score_qualidade",
        "nivel_qualidade",
        "flag_revisao_manual",
        "motivos_revisao",
    ]]


def build_metodologia_dimension(df: pd.DataFrame) -> pd.DataFrame:
    dim = (
        df[["bi_familia_do_metodo", "bi_tipo_estudo_futuro", "aplicou_estudo_futuro", "aplicou_estudo_futuro_status"]]
        .drop_duplicates()
        .reset_index(drop=True)
        .rename(columns={
            "bi_familia_do_metodo": "familia_do_metodo",
            "bi_tipo_estudo_futuro": "tipo_estudo_futuro",
        })
    )
    dim["familia_do_metodo"] = dim["familia_do_metodo"].apply(lambda v: fill_text(v, "Não classificado"))
    dim["tipo_estudo_futuro"] = dim["tipo_estudo_futuro"].apply(lambda v: fill_text(v, "Não informado"))
    dim["natureza_metodologia"] = dim["familia_do_metodo"].apply(classify_method_nature)
    dim["id_metodologia_hash"] = [
        stable_hash_id("mdg", row.familia_do_metodo, row.tipo_estudo_futuro, row.aplicou_estudo_futuro)
        for row in dim.itertuples(index=False)
    ]
    dim = add_surrogate_key(
        dim[[
            "id_metodologia_hash",
            "familia_do_metodo",
            "natureza_metodologia",
            "tipo_estudo_futuro",
            "aplicou_estudo_futuro",
            "aplicou_estudo_futuro_status",
        ]],
        "sk_metodologia",
        ["id_metodologia_hash"],
    )
    return dim


def build_dimensions_and_bridges(df_raw: pd.DataFrame, settings=None) -> dict[str, pd.DataFrame]:
    df = prepare_bi_dataframe(df_raw)

    dim_documento = build_document_dimension(df)
    doc_sk_map = dim_documento[["sk_documento", "id_documento_hash"]].rename(columns={"id_documento_hash": "id_documento_logico"})

    dim_tempo = build_time_dimension(df)
    dim_setor, ponte_setor = explode_dimension_with_bridge(df, "id_documento_logico", "bi_setores", "setor", "set", doc_sk_map, "sk_setor")
    dim_abrangencia, ponte_abrangencia = explode_dimension_with_bridge(df, "id_documento_logico", "bi_abrangencias", "abrangencia", "abr", doc_sk_map, "sk_abrangencia")
    dim_instituicao_responsavel = build_simple_dimension(df, "bi_instituicao_responsavel", "ins", "instituicao", "sk_instituicao")

    theme_dict = load_review_dictionary(settings, "dicionario_temas.csv")
    dim_tema, ponte_tema = build_theme_dimension_and_bridge(df, doc_sk_map, theme_dict)
    dim_metodo, ponte_metodo = build_method_dimension_and_bridge(df, doc_sk_map)
    dim_apoio, ponte_apoio = explode_dimension_with_bridge(df, "id_documento_logico", "bi_instituicoes_apoio", "instituicao_apoio", "iap", doc_sk_map, "sk_instituicao_apoio")
    dim_ref, ponte_ref = explode_dimension_with_bridge(df, "id_documento_logico", "referencias", "referencia", "ref", doc_sk_map, "sk_referencia")
    dim_cond, ponte_cond = explode_dimension_with_bridge(df, "id_documento_logico", "condicionantes_estudo_futuro", "condicionante", "con", doc_sk_map, "sk_condicionante")
    dim_source_file, ponte_source_file = explode_dimension_with_bridge(df, "id_documento_logico", "source_files", "arquivo_origem", "src", doc_sk_map, "sk_source_file")

    inst_dict = load_merged_dictionary(settings, "dicionario_instituicoes.csv", "dicionario_instituicoes_enriquecido.csv")
    method_dict = load_merged_dictionary(settings, "dicionario_metodos.csv", "dicionario_metodos_taxonomia.csv")
    cond_dict = load_merged_dictionary(settings, "dicionario_condicionantes.csv", "dicionario_condicionantes_cluster.csv")

    dim_instituicao_responsavel = apply_institution_enrichment(dim_instituicao_responsavel, inst_dict, "instituicao")
    dim_apoio = apply_institution_enrichment(dim_apoio, inst_dict, "instituicao_apoio")
    dim_metodo = apply_method_taxonomy_enrichment(dim_metodo, method_dict)
    dim_cond = apply_condition_enrichment(dim_cond, cond_dict)

    dim_metodologia = build_metodologia_dimension(df)
    dim_qualidade = build_quality_dimension(df, doc_sk_map)

    return {
        "dim_documento": dim_documento,
        "dim_tempo": dim_tempo,
        "dim_setor": dim_setor,
        "dim_abrangencia": dim_abrangencia,
        "dim_instituicao_responsavel": dim_instituicao_responsavel,
        "dim_tema": dim_tema,
        "dim_metodo": dim_metodo,
        "dim_apoio": dim_apoio,
        "dim_referencia": dim_ref,
        "dim_condicionante": dim_cond,
        "dim_source_file": dim_source_file,
        "dim_metodologia": dim_metodologia,
        "dim_qualidade": dim_qualidade,
        "ponte_documento_tema": ponte_tema,
        "ponte_documento_metodo": ponte_metodo,
        "ponte_documento_instituicao_apoio": ponte_apoio,
        "ponte_documento_referencia": ponte_ref,
        "ponte_documento_condicionante": ponte_cond,
        "ponte_documento_arquivo_origem": ponte_source_file,
        "ponte_documento_setor": ponte_setor,
        "ponte_documento_abrangencia": ponte_abrangencia,
    }
