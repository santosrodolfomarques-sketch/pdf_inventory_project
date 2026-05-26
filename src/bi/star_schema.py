from __future__ import annotations

import pandas as pd

from src.bi.bridges import add_surrogate_key, build_simple_dimension, explode_dimension_with_bridge
from src.bi.dimensions import prepare_bi_dataframe, load_enrichment_dictionary, apply_institution_enrichment, apply_condition_enrichment, build_metodologia_dimension, build_time_dimension
from src.bi.facts import build_fact_inventory
from src.bi.semantic_helpers import (
    choose_list,
    choose_scalar,
    classify_macrotema,
    classify_macro_setor,
    classify_nivel_abrangencia,
    classify_pais_abrangencia,
    classify_subtema,
    coalesce_text,
    quality_level,
)
from src.core.config import Settings
from src.shared.ids import stable_hash_id


def build_star_schema(df_raw: pd.DataFrame, settings: Settings) -> dict[str, pd.DataFrame]:
    """
    Constrói a modelagem completa Star Schema a partir da base normalizada.
    
    Aplica cálculo dinâmico de qualidade do documento usando os pesos parametrizados:
    - settings.weight_name
    - settings.weight_year
    - settings.weight_horizon
    - settings.weight_sector
    - settings.weight_scope
    - settings.weight_themes
    - settings.weight_refs
    - settings.weight_methods
    """
    df = prepare_bi_dataframe(df_raw)

    # 1. Dimensão Documento
    cols = ["id_documento_logico", "bi_nome_documento", "sigla_ou_abreviacao", "bi_tipo_documento", "bi_instituicao_responsavel", "qtd_arquivos_origem"]
    existing = [c for c in cols if c in df.columns]
    dim_doc = df[existing].drop_duplicates().rename(columns={
        "id_documento_logico": "id_documento_hash",
        "bi_nome_documento": "nome_documento",
        "bi_tipo_documento": "tipo_documento",
        "bi_instituicao_responsavel": "instituicao_responsavel",
    })
    dim_doc = add_surrogate_key(dim_doc, "sk_documento", ["id_documento_hash"])

    doc_sk_map = dim_doc[["sk_documento", "id_documento_hash"]].rename(columns={"id_documento_hash": "id_documento_logico"})

    # 2. Dimensão Tempo
    dim_tempo = build_time_dimension(df)

    # 3. Dimensão Setor
    dim_setor = build_simple_dimension(df, "bi_setor", "set", "setor", "sk_setor")
    dim_setor["macro_setor"] = dim_setor["setor"].apply(classify_macro_setor)

    # 4. Dimensão Abrangência
    dim_abrangencia = build_simple_dimension(df, "bi_abrangencia", "abr", "abrangencia", "sk_abrangencia")
    dim_abrangencia["nivel_abrangencia"] = dim_abrangencia["abrangencia"].apply(classify_nivel_abrangencia)
    dim_abrangencia["pais"] = dim_abrangencia["abrangencia"].apply(classify_pais_abrangencia)

    # 5. Dimensão Instituição Responsável
    dim_inst_resp = build_simple_dimension(df, "bi_instituicao_responsavel", "ins", "instituicao", "sk_instituicao")

    # 6. Dimensões Multivaloradas e Pontes (Temas, Métodos, Apoio, Condicionantes, Referências, Fontes)
    dim_tema, ponte_tema = _build_theme_dimension_and_bridge(df, doc_sk_map)
    dim_metodo, ponte_metodo = _build_method_dimension_and_bridge(df, doc_sk_map)

    dim_apoio, ponte_apoio = explode_dimension_with_bridge(df, "id_documento_logico", "bi_instituicoes_apoio", "instituicao_apoio", "iap", doc_sk_map, "sk_instituicao_apoio")
    dim_ref, ponte_ref = explode_dimension_with_bridge(df, "id_documento_logico", "referencias", "referencia", "ref", doc_sk_map, "sk_referencia")
    dim_cond, ponte_cond = explode_dimension_with_bridge(df, "id_documento_logico", "condicionantes_estudo_futuro", "condicionante", "con", doc_sk_map, "sk_condicionante")
    dim_source_file, ponte_source_file = explode_dimension_with_bridge(df, "id_documento_logico", "source_files", "arquivo_origem", "src", doc_sk_map, "sk_source_file")

    # Enriquecimentos Inteligentes via Dicionários de IA/Clusters
    inst_dict = load_enrichment_dictionary(settings, "dicionario_instituicoes_enriquecido.csv")
    cond_dict = load_enrichment_dictionary(settings, "dicionario_condicionantes_cluster.csv")

    dim_inst_resp = apply_institution_enrichment(dim_inst_resp, inst_dict, "instituicao")
    dim_apoio = apply_institution_enrichment(dim_apoio, inst_dict, "instituicao_apoio")
    dim_cond = apply_condition_enrichment(dim_cond, cond_dict)

    # 7. Dimensão Metodologia
    dim_metodologia = build_metodologia_dimension(df)

    # 8. Cálculo Dinâmico da Dimensão Qualidade usando os Pesos Parametrizados
    dim_qualidade = _build_dynamic_quality_dimension(df, doc_sk_map, settings)

    dimensions = {
        "dim_documento": dim_doc,
        "dim_tempo": dim_tempo,
        "dim_setor": dim_setor,
        "dim_abrangencia": dim_abrangencia,
        "dim_instituicao_responsavel": dim_inst_resp,
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
    }

    # 9. Fato Inventário Principal
    fact = build_fact_inventory(df_raw, dimensions)

    dimensions["fato_inventario"] = fact
    return dimensions


def _build_theme_dimension_and_bridge(df: pd.DataFrame, doc_sk_map: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = df[["id_documento_logico", "bi_temas"]].explode("bi_temas").dropna()
    base = base[base["bi_temas"].astype(str).str.strip() != ""]
    base = base.rename(columns={"bi_temas": "tema"})

    dim = base[["tema"]].drop_duplicates().reset_index(drop=True)
    dim["macrotema"] = dim["tema"].apply(classify_macrotema)
    dim["subtema"] = dim["tema"].apply(classify_subtema)
    dim["id_tema_hash"] = [stable_hash_id("tem", row.tema) for row in dim.itertuples(index=False)]
    dim = add_surrogate_key(dim[["id_tema_hash", "tema", "macrotema", "subtema"]], "sk_tema", ["id_tema_hash"])

    ponte = base.merge(dim[["sk_tema", "id_tema_hash", "tema"]], on="tema", how="left")
    ponte = ponte.merge(doc_sk_map, on="id_documento_logico", how="left")
    return dim, ponte[["sk_documento", "id_documento_logico", "sk_tema", "id_tema_hash"]].drop_duplicates().reset_index(drop=True)


def _build_method_dimension_and_bridge(df: pd.DataFrame, doc_sk_map: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = df[["id_documento_logico", "bi_metodos", "bi_familia_do_metodo"]].explode("bi_metodos").dropna()
    base = base[base["bi_metodos"].astype(str).str.strip() != ""]
    base = base.rename(columns={"bi_metodos": "metodo"})

    dim = base[["metodo", "bi_familia_do_metodo"]].drop_duplicates().reset_index(drop=True)
    from src.bi.semantic_helpers import classify_method_family, classify_method_nature
    dim["familia_do_metodo"] = dim.apply(lambda r: classify_method_family(r["metodo"], r.get("bi_familia_do_metodo")), axis=1)
    dim["natureza_metodo"] = dim.apply(lambda r: classify_method_nature(r["familia_do_metodo"], r["metodo"]), axis=1)
    dim["id_metodo_hash"] = [stable_hash_id("met", r.metodo, r.familia_do_metodo) for r in dim.itertuples(index=False)]
    dim = add_surrogate_key(dim[["id_metodo_hash", "metodo", "familia_do_metodo", "natureza_metodo"]], "sk_metodo", ["id_metodo_hash"])

    ponte = base.merge(dim[["sk_metodo", "id_metodo_hash", "metodo"]], on="metodo", how="left")
    ponte = ponte.merge(doc_sk_map, on="id_documento_logico", how="left")
    return dim, ponte[["sk_documento", "id_documento_logico", "sk_metodo", "id_metodo_hash"]].drop_duplicates().reset_index(drop=True)


def _build_dynamic_quality_dimension(df: pd.DataFrame, doc_sk_map: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    """Calcula dinamicamente a dimensão de qualidade baseada nos pesos configuráveis."""
    quality_rows = []

    for row in df.itertuples(index=False):
        qtd_temas = len(getattr(row, "bi_temas", []) or [])
        qtd_metodos = len(getattr(row, "bi_metodos", []) or [])
        qtd_referencias = len(getattr(row, "referencias", []) or [])

        possui_nome = bool(coalesce_text(getattr(row, "bi_nome_documento", None)))
        possui_ano = pd.notna(getattr(row, "ano_publicacao", None))
        possui_horizonte = pd.notna(getattr(row, "horizonte_temporal", None))
        possui_setor = coalesce_text(getattr(row, "bi_setor", None)) not in {None, "Não informado"}
        possui_abrangencia = coalesce_text(getattr(row, "bi_abrangencia", None)) not in {None, "Não informado"}
        aplicou_estudo = bool(getattr(row, "aplicou_estudo_futuro", False))

        # Cálculo do score ponderado dinamicamente
        score = 0.0
        score += settings.weight_name if possui_nome else 0.0
        score += settings.weight_year if possui_ano else 0.0
        score += settings.weight_horizon if possui_horizonte else 0.0
        score += settings.weight_sector if possui_setor else 0.0
        score += settings.weight_scope if possui_abrangencia else 0.0
        score += settings.weight_themes if qtd_temas > 0 else 0.0
        score += settings.weight_refs if qtd_referencias > 0 else 0.0
        score += settings.weight_methods if (not aplicou_estudo or qtd_metodos > 0) else 0.0
        score = min(round(score, 3), 1.0)

        motivos = []
        if not possui_nome: motivos.append("nome_documento_ausente")
        if not possui_ano: motivos.append("ano_publicacao_ausente")
        if aplicou_estudo and qtd_metodos == 0: motivos.append("estudo_futuro_sem_metodo")
        if not possui_setor: motivos.append("setor_nao_informado")
        if not possui_abrangencia: motivos.append("abrangencia_nao_informada")

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

    return dim[["sk_qualidade", "id_qualidade_hash", "sk_documento", "id_documento_logico", "score_qualidade", "nivel_qualidade", "flag_revisao_manual", "motivos_revisao"]]
