from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.config import Settings
from src.shared.ids import stable_hash_id
from src.shared.utils import read_json, to_json_string
from src.transformation.cleansing import clean_list, clean_string, clean_year, remove_accents

LIST_COLUMNS = [
    "temas",
    "temas_norm",
    "metodos_estudo_futuro",
    "metodos_estudo_futuro_norm",
    "referencias",
    "condicionantes_estudo_futuro",
    "instituicoes_apoio",
    "instituicoes_apoio_norm",
    "source_files",
]


def generate_abbreviation(name: str | None) -> str:
    """Gera uma sigla/abreviação estável baseada nas primeiras letras das palavras."""
    if not name:
        return "S_N"
    stopwords = {
        "de", "do", "da", "dos", "das", "e", "para", "com", "em",
        "no", "na", "o", "a", "os", "as", "the", "of", "and",
    }
    words = [w for w in re.findall(r"\b\w+\b", str(name)) if w.lower() not in stopwords]
    initials = [w[0].upper() for w in words if w]
    return "".join(initials[:12]) or "S_N"


import re


def infer_aplicou_estudo_futuro(
    extracted_flag: bool | None,
    nome: str | None,
    horizonte: int | None,
    tipo: str | None,
    metodos: list[str],
) -> bool | None:
    """Inspeciona sinais linguísticos para deduzir se um estudo de futuro foi aplicado."""
    if len(metodos) >= 1:
        return True
    corpus = " | ".join(item.lower() for item in [nome or "", tipo or ""] + metodos if item)
    corpus = remove_accents(corpus)

    strong_signals = [
        "cenario", "scenario", "foresight", "backcasting", "delphi", "modelagem",
        "simulacao", "projecao", "forecast", "estudo de futuro"
    ]
    if any(sig in corpus for sig in strong_signals):
        return True
    if extracted_flag is False:
        return False
    return extracted_flag


def process_record(payload: dict[str, Any], metadata: dict[str, Any], settings: Settings) -> dict[str, Any]:
    """Aplica as regras de negócio iniciais e formatação rígida a um registro bruto."""
    nome = clean_string(payload.get("nome_documento"))
    tipo = clean_string(payload.get("tipo_documento"))
    ano = clean_year(payload.get("ano_publicacao"))
    horizonte = clean_year(payload.get("horizonte_temporal"))
    abrangencia = clean_string(payload.get("abrangencia_territorial"))
    setor = clean_string(payload.get("setor"))
    tipo_estudo = clean_string(payload.get("tipo_estudo_futuro"))
    inst_resp = clean_string(payload.get("instituicao_responsavel"))

    temas = clean_list(payload.get("temas"))
    metodos = clean_list(payload.get("metodos_estudo_futuro"))
    referencias = clean_list(payload.get("referencias"))
    condicionantes = clean_list(payload.get("condicionantes_estudo_futuro"))
    apoio = clean_list(payload.get("instituicoes_apoio"))

    aplicou = infer_aplicou_estudo_futuro(
        payload.get("aplicou_estudo_futuro"),
        nome,
        horizonte,
        tipo_estudo,
        metodos,
    )

    extensao = None
    if isinstance(ano, int) and isinstance(horizonte, int):
        extensao = horizonte - ano

    # Geração de Hashes de Negócio Estáveis
    id_arquivo = stable_hash_id("arq", metadata.get("source_file_hash"), metadata.get("source_file_name"))
    id_documento_logico = stable_hash_id("doc", nome or metadata.get("source_file_name"), inst_resp or "indefinido", ano or 0)

    # Flags de qualidade/revisão manual inicial
    flag_revisao = any([
        not nome,
        ano is None,
        not tipo,
        aplicou is None,
    ])

    return {
        "id_arquivo": id_arquivo,
        "id_documento_logico": id_documento_logico,
        "source_file_name": metadata.get("source_file_name"),
        "source_file_hash": metadata.get("source_file_hash"),
        "processed_at_utc": metadata.get("processed_at_utc"),
        "nome_documento": nome,
        "nome_documento_norm": nome,  # Fallback inicial antes da IA
        "sigla_ou_abreviacao": generate_abbreviation(nome),
        "tipo_documento": tipo,
        "tipo_documento_norm": tipo,  # Fallback inicial antes da IA
        "ano_publicacao": ano,
        "horizonte_temporal": horizonte,
        "extensao_tempo": extensao,
        "abrangencia_territorial": abrangencia,
        "abrangencia_territorial_norm": abrangencia,  # Fallback
        "setor": setor,
        "setor_norm": setor,  # Fallback
        "temas": temas,
        "temas_norm": temas,  # Fallback
        "aplicou_estudo_futuro": aplicou,
        "tipo_estudo_futuro": tipo_estudo,
        "tipo_estudo_futuro_norm": tipo_estudo,  # Fallback
        "metodos_estudo_futuro": metodos,
        "metodos_estudo_futuro_norm": metodos,  # Fallback
        "familia_do_metodo": None,
        "familia_do_metodo_norm": None,
        "instituicao_responsavel": inst_resp,
        "instituicao_responsavel_norm": inst_resp,  # Fallback
        "instituicoes_apoio": apoio,
        "instituicoes_apoio_norm": apoio,  # Fallback
        "referencias": referencias,
        "condicionantes_estudo_futuro": condicionantes,
        "flag_revisao_manual": flag_revisao,
    }


def _consolidate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Consolida documentos lógicos repetidos agrupando suas origens e mesclando listas."""
    grouped = defaultdict(list)
    for rec in records:
        grouped[rec["id_documento_logico"]].append(rec)

    consolidated = []
    for doc_id, group in grouped.items():
        base = dict(group[0])
        base["qtd_arquivos_origem"] = len(group)
        base["source_files"] = sorted(list(set(item["source_file_name"] for item in group if item.get("source_file_name"))))

        # Mescla listas sem duplicações
        for field in ["temas", "temas_norm", "metodos_estudo_futuro", "metodos_estudo_futuro_norm", "referencias", "condicionantes_estudo_futuro", "instituicoes_apoio", "instituicoes_apoio_norm"]:
            combined = []
            for rec in group:
                combined.extend(rec.get(field, []))
            # Deduplica preservando ordem lógica
            seen = set()
            base[field] = [item for item in combined if not (item.lower() in seen or seen.add(item.lower()))]

        # Coalesce campos escalares (pega o primeiro preenchido)
        scalar_fields = ["nome_documento", "tipo_documento", "ano_publicacao", "horizonte_temporal", "extensao_tempo", "abrangencia_territorial", "setor", "instituicao_responsavel", "tipo_estudo_futuro"]
        for field in scalar_fields:
            for item in group:
                if item.get(field) is not None:
                    base[field] = item[field]
                    break
        consolidated.append(base)

    return consolidated


def _save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def run_transformation(settings: Settings, logger: Any) -> dict[str, Any]:
    """Executa a transformação inicial, higieniza tipos e exporta valores únicos para normalização IA."""
    json_files = sorted(Path(settings.extracted_json_dir).glob("*.json"))

    if not json_files:
        logger.info("Nenhum arquivo JSON extraído encontrado.")
        return {"processed": 0, "status": "empty"}

    raw_records = []
    for path in json_files:
        try:
            data = read_json(path)
            processed = process_record(data.get("payload", {}), data.get("metadata", {}), settings)
            raw_records.append(processed)
        except Exception as exc:
            logger.exception(f"Erro ao processar registro {path.name}: {exc}")

    # Remove duplicados exatos (mesmo arquivo hash e chaves de negócio)
    unique_raw = []
    seen_hashes = set()
    for rec in raw_records:
        h = (rec["source_file_hash"], rec["id_documento_logico"])
        if h not in seen_hashes:
            seen_hashes.add(h)
            unique_raw.append(rec)

    # Consolida em documentos lógicos unificados
    consolidated_records = _consolidate_records(unique_raw)

    # Serializa listas em JSON string para salvar em CSV
    def serialize_lists(recs: list[dict[str, Any]]) -> pd.DataFrame:
        serialized = []
        for r in recs:
            row = dict(r)
            for col in LIST_COLUMNS:
                if col in row:
                    row[col] = to_json_string(row[col])
            serialized.append(row)
        return pd.DataFrame(serialized)

    base_df = serialize_lists(unique_raw)
    consolidated_df = serialize_lists(consolidated_records)

    _save_csv(base_df, settings.transformed_base_dir / "documentos_tratados.csv")
    _save_csv(consolidated_df, settings.transformed_base_dir / "documentos_consolidados.csv")

    # GERAÇÃO DE VALORES ÚNICOS PARA NORMALIZAÇÃO IA (Batch Prep)
    unique_fields = ["tipo_documento", "abrangencia_territorial", "setor", "instituicao_responsavel", "tipo_estudo_futuro"]
    for field in unique_fields:
        unique_vals = sorted(list(set(
            rec[field] for rec in consolidated_records if rec.get(field)
        )))
        df_vals = pd.DataFrame({"valor_original": unique_vals})
        _save_csv(df_vals, settings.transformed_unique_dir / f"valores_unicos_{field}.csv")

    # Extrai instituições de apoio (mesclando da lista)
    apoio_vals = set()
    for rec in consolidated_records:
        for val in rec.get("instituicoes_apoio", []):
            if val:
                apoio_vals.add(val)
    # Mescla apoio e instituição responsável sob a mesma dimensão de normalização de 'instituicoes'
    inst_completo = sorted(list(apoio_vals.union(set(rec["instituicao_responsavel"] for rec in consolidated_records if rec.get("instituicao_responsavel")))))
    _save_csv(pd.DataFrame({"valor_original": inst_completo}), settings.transformed_unique_dir / "valores_unicos_instituicao_responsavel.csv")

    # Extrai condicionantes únicas
    cond_vals = set()
    for rec in consolidated_records:
        for val in rec.get("condicionantes_estudo_futuro", []):
            if val:
                cond_vals.add(val)
    _save_csv(pd.DataFrame({"valor_original": sorted(list(cond_vals))}), settings.transformed_unique_dir / "valores_unicos_condicionantes.csv")

    # Extrai temas únicos por frequência (top 150 para evitar sobrecarga de API)
    tema_counts = defaultdict(int)
    for rec in consolidated_records:
        for val in rec.get("temas", []):
            if val:
                tema_counts[val] += 1
    sorted_temas = [t for t, _ in sorted(tema_counts.items(), key=lambda x: x[1], reverse=True)]
    _save_csv(pd.DataFrame({"valor_original": sorted_temas[:150]}), settings.transformed_unique_dir / "valores_unicos_temas.csv")

    # Extrai métodos únicos por frequência (top 150)
    metodo_counts = defaultdict(int)
    for rec in consolidated_records:
        for val in rec.get("metodos_estudo_futuro", []):
            if val:
                metodo_counts[val] += 1
    sorted_metodos = [m for m, _ in sorted(metodo_counts.items(), key=lambda x: x[1], reverse=True)]
    _save_csv(pd.DataFrame({"valor_original": sorted_metodos[:150]}), settings.transformed_unique_dir / "valores_unicos_metodos.csv")

    logger.info("Transformação e consolidação lógica concluídas com sucesso.")
    return {
        "processed": len(unique_raw),
        "consolidated": len(consolidated_records),
        "status": "ok",
    }
