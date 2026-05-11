from __future__ import annotations

import ast
import json
import math
import re
import unicodedata
from typing import Any

import pandas as pd

GENERIC_VALUES = {
    "",
    "nan",
    "none",
    "null",
    "outro",
    "outros",
    "nao classificado",
    "não classificado",
    "nao informado",
    "não informado",
    "outros / nao classificado",
    "outros / não classificado",
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def strip_accents_lower(value: Any) -> str:
    text = normalize_text(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def coalesce_text(*values: Any, default: str | None = None) -> str | None:
    for value in values:
        text = normalize_text(value)
        if text and text.lower() not in {"nan", "none", "null"}:
            return text
    return default


def is_generic_value(value: Any) -> bool:
    return strip_accents_lower(value) in GENERIC_VALUES


def safe_parse_list(value: Any) -> list[str]:
    """Converte listas serializadas em listas Python, preservando strings uteis."""
    if value is None:
        return []
    if isinstance(value, float) and math.isnan(value):
        return []
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in {"nan", "none", "null"}:
            return []
        if text.startswith("[") and text.endswith("]"):
            try:
                raw_items = json.loads(text)
            except Exception:
                try:
                    raw_items = ast.literal_eval(text)
                except Exception:
                    raw_items = [text]
        else:
            raw_items = [text]
    else:
        raw_items = [value]

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = normalize_text(item)
        if not text or text.lower() in {"nan", "none", "null"}:
            continue
        key = strip_accents_lower(text)
        if key not in seen:
            seen.add(key)
            cleaned.append(text)
    return cleaned


def choose_scalar(df: pd.DataFrame, base_col: str, default: str | None = None) -> pd.Series:
    """Escolhe coluna normalizada quando existir; caso contrario, usa a coluna bruta."""
    norm_col = f"{base_col}_norm"
    if norm_col in df.columns and base_col in df.columns:
        chosen = df[norm_col].where(df[norm_col].notna() & (df[norm_col].astype(str).str.strip() != ""), df[base_col])
    elif norm_col in df.columns:
        chosen = df[norm_col]
    elif base_col in df.columns:
        chosen = df[base_col]
    else:
        chosen = pd.Series([default] * len(df), index=df.index)

    chosen = chosen.apply(lambda value: coalesce_text(value, default=default))
    if default is not None:
        chosen = chosen.fillna(default)
    return chosen


def choose_list(df: pd.DataFrame, base_col: str) -> pd.Series:
    """Escolhe lista normalizada quando existir; caso contrario, usa lista bruta."""
    norm_col = f"{base_col}_norm"
    source_col = norm_col if norm_col in df.columns else base_col
    if source_col not in df.columns:
        return pd.Series([[] for _ in range(len(df))], index=df.index)
    return df[source_col].apply(safe_parse_list)


def _match(text: str, keywords: list[str]) -> bool:
    return any(strip_accents_lower(keyword) in text for keyword in keywords)


def classify_macrotema(tema: Any) -> str:
    text = strip_accents_lower(tema)
    rules = [
        ("Agenda 2030 e ODS", ["ods", "sdg", "sustainable development goals", "agenda 2030", "2030 agenda"]),
        ("Meio Ambiente e Clima", ["clima", "climate", "ambient", "environment", "floresta", "desmat", "oceano", "biodivers", "ecossistema", "sustentab", "residuo", "carbon", "emisso", "poluicao", "saneamento", "agua", "recursos hidricos", "servicos ecossistemicos", "conservacao", "restauracao"]),
        ("Energia e Recursos Naturais", ["energia", "energy", "petroleo", "gas natural", "pre-sal", "hidrogenio", "biocombust", "eletric", "mineracao", "mineral", "recursos energeticos"]),
        ("Infraestrutura e Território", ["infraestrutura", "transporte", "logistica", "mobilidade", "habitacao", "housing", "cidade", "urbano", "regional", "territorial", "metropole", "metropolitana", "porto", "aeroporto"]),
        ("Desenvolvimento Social", ["pobreza", "fome", "hunger", "seguranca alimentar", "saude", "health", "educacao", "education", "genero", "gender", "desigual", "inequal", "direitos humanos", "violencia", "voluntariado", "mortalidade", "homelessness", "moradia"]),
        ("Economia e Trabalho", ["econom", "growth", "trabalho", "emprego", "renda", "produt", "industr", "capital", "mercado", "competitiv", "contas publicas", "fiscal", "orcamento", "financiamento", "cadeia produtiva", "comercio", "export"]),
        ("Governança e Instituições", ["govern", "democr", "politica publica", "public policy", "institu", "paz", "peace", "justica", "multilateral", "transpar", "seguranca publica", "regulatorio", "regulacao", "gestao publica", "participacao social"]),
        ("Ciência, Tecnologia e Inovação", ["ciencia", "science", "tecnolog", "inov", "innovation", "inteligencia artificial", "ia", "i.a", "digital", "realidade virtual", "cidades inteligentes", "dados", "data", "pesquisa", "conhecimento", "modelo logico"]),
        ("Segurança e Defesa", ["defesa", "seguranca nacional", "seguranca de transportes", "criminal", "drogas", "armas", "fronteira"]),
        ("Agropecuária e Alimentação", ["agro", "agric", "pecuaria", "pesca", "aquicultura", "alimento", "alimentar", "rural", "bioeconomia"]),
    ]
    for macrotema, keywords in rules:
        if _match(text, keywords):
            return macrotema
    return "Outros / Não Classificado"


def classify_subtema(tema: Any) -> str:
    text = strip_accents_lower(tema)
    rules = [
        ("ODS / Agenda 2030", ["ods", "sdg", "agenda 2030", "sustainable development goals"]),
        ("Clima", ["clima", "climate", "carbon", "emisso", "poluicao do ar"]),
        ("Biodiversidade e Ecossistemas", ["biodivers", "ecossistema", "floresta", "desmat", "ocean", "marine", "servicos ecossistemicos", "conservacao", "restauracao", "especies ameacadas"]),
        ("Saneamento e Resíduos", ["saneamento", "residuo", "lixo", "agua potavel", "esgoto"]),
        ("Recursos Hídricos", ["agua", "recursos hidricos", "hidrico", "bacia hidrografica"]),
        ("Energia", ["energia", "energy", "energetic", "energetico", "energeticos", "petroleo", "gas natural", "hidrogenio", "eletric", "biocombust"]),
        ("Mineração", ["mineracao", "mineral", "geologico", "pre-sal"]),
        ("Transporte e Logística", ["transporte", "logistica", "mobilidade", "porto", "aeroporto", "rodovia", "ferrovia"]),
        ("Cidades e Habitação", ["habitacao", "housing", "homelessness", "moradia", "cidade", "urbano", "metropole", "territorial"]),
        ("Pobreza e Desigualdade", ["pobreza", "desigual", "inequal", "hunger", "fome", "seguranca alimentar"]),
        ("Saúde", ["saude", "health", "covid", "mortalidade", "sanitaria"]),
        ("Educação", ["educacao", "education", "ensino", "aprendizagem"]),
        ("Gênero e Diversidade", ["genero", "gender", "mulher", "racismo", "indigena", "quilombola", "pluralidade", "diversidade"]),
        ("Trabalho e Renda", ["trabalho", "emprego", "renda", "qualificacao", "produtividade"]),
        ("Indústria e Competitividade", ["industr", "competitiv", "cadeia produtiva", "manufatura"]),
        ("Finanças Públicas", ["contas publicas", "fiscal", "orcamento", "financiamento", "credito"]),
        ("Governança", ["govern", "democr", "institu", "multilateral", "participacao social", "gestao publica", "politica publica"]),
        ("Segurança e Defesa", ["defesa", "seguranca", "drogas", "armas", "criminal"]),
        ("Tecnologia", ["tecnolog", "digital", "inteligencia artificial", "ia", "i.a", "virtual", "dados", "data", "inovacao", "modelo logico"]),
        ("Agropecuária e Alimentação", ["agro", "agric", "pecuaria", "pesca", "aquicultura", "alimento", "alimentar", "rural"]),
    ]
    for subtema, keywords in rules:
        if _match(text, keywords):
            return subtema
    return "Outros"


def classify_method_family(metodo: Any, familia_hint: Any = None) -> str:
    hint = coalesce_text(familia_hint)
    if hint and not is_generic_value(hint):
        return hint
    text = strip_accents_lower(metodo)
    rules = [
        ("Cenários Prospectivos", ["cenario", "scenario", "prospectiv", "foresight", "cenarizacao", "prospeccao", "signals scanning", "horizon scanning", "weak signals"]),
        ("Extrapolação de Tendências", ["tendencia", "trend", "series temporais", "forecast", "previs", "projecao", "projecoes", "extrapol"]),
        ("Painel de Especialistas (Delphi/Workshops)", ["delphi", "workshop", "oficina", "seminario", "grupo focal", "focus group", "painel", "especialista", "consulta", "entrevista", "plenaria", "conferencia", "dialogo"]),
        ("Modelagem e Simulação Quantitativa", ["modelagem", "simulacao", "modelo", "econometr", "microssimul", "matriz", "quantit", "frequencia de respostas"]),
        ("Visão de Futuro / Backcasting", ["backcasting", "visao de futuro", "roadmap", "visioning", "visao estrategica"]),
        ("Planejamento Estratégico / Roadmapping", ["planejamento estrategico", "plano estrategico", "roadmapping", "missao", "orientado por missoes", "strategic planning"]),
        ("Monitoramento e Indicadores", ["indicador", "monitoramento", "avaliacao", "meta", "classificacao"]),
        ("Análise Documental e Bibliográfica", ["bibliograf", "documental", "literatura", "referencia", "scielo", "capes", "leitura critica", "analise documental", "politicas publicas"]),
    ]
    for family, keywords in rules:
        if _match(text, keywords):
            return family
    return "Outros / Não Classificado"


def classify_method_nature(familia: Any, metodo: Any = None) -> str:
    text = strip_accents_lower(f"{familia or ''} {metodo or ''}")
    if _match(text, ["modelagem", "simulacao", "quantit", "indicador", "series", "forecast", "frequencia", "tendencia", "projecao", "previsao", "extrapolacao"]):
        return "Quantitativo"
    if _match(text, ["delphi", "workshop", "oficina", "seminario", "grupo focal", "painel", "entrevista", "consulta", "plenaria", "dialogo", "conferencia"]):
        return "Qualitativo"
    if _match(text, ["cenario", "prospect", "foresight", "backcasting", "visao de futuro", "roadmap", "planejamento estrategico", "strategic planning"]):
        return "Prospectivo"
    if _match(text, ["bibliograf", "documental", "literatura", "leitura critica"]):
        return "Documental"
    return "Não Classificado"


def classify_macro_setor(setor: Any) -> str:
    text = strip_accents_lower(setor)
    rules = [
        ("Meio Ambiente e Clima", ["clima", "ambient", "meio ambiente", "residuo", "saneamento", "recursos hidricos"]),
        ("Energia e Recursos Naturais", ["energia", "energetico", "mineracao", "mineral", "petroleo", "gas"]),
        ("Infraestrutura e Território", ["infraestrutura", "transporte", "logistica", "habitacao", "urbano", "regional", "territorial", "aviacao"]),
        ("Desenvolvimento Social", ["saude", "educacao", "social", "direitos", "pobreza", "sociedade civil", "terceiro setor"]),
        ("Economia e Trabalho", ["econom", "industr", "trabalho", "emprego", "renda", "produt", "agro", "comercio"]),
        ("Governança e Setor Público", ["administracao publica", "governo", "planejamento governamental", "politica publica", "seguranca"]),
        ("Ciência, Tecnologia e Inovação", ["tecnologia", "digital", "inovacao", "data centers", "propriedade intelectual"]),
        ("Multissetorial", ["multissetorial", "desenvolvimento", "public policy", "development"]),
    ]
    for macro_setor, keywords in rules:
        if _match(text, keywords):
            return macro_setor
    return "Outros / Não Classificado"


def classify_nivel_abrangencia(value: Any) -> str:
    text = strip_accents_lower(value)
    if is_generic_value(text):
        return "Não informado"
    if text in {"global", "internacional", "international"}:
        return "Global"
    if text in {"nacional", "brasil", "brazil"}:
        return "Nacional"
    if text in {"france", "ireland"}:
        return "País estrangeiro"
    states = {
        "acre", "alagoas", "amapa", "amazonas", "bahia", "ceara", "distrito federal",
        "espirito santo", "goias", "maranhao", "mato grosso", "mato grosso do sul",
        "minas gerais", "para", "paraiba", "parana", "pernambuco", "piaui",
        "rio de janeiro", "rio grande do norte", "rio grande do sul", "rondonia",
        "roraima", "santa catarina", "sao paulo", "sergipe", "tocantins",
    }
    if text.startswith("estado ") or text in states:
        return "Estadual"
    if _match(text, ["metropole", "macrometropole", "regiao metropolitana", "regional"]):
        return "Regional"
    return "Municipal/Local"


def classify_pais_abrangencia(value: Any) -> str:
    text = strip_accents_lower(value)
    if text == "france":
        return "França"
    if text == "ireland":
        return "Irlanda"
    if text == "global":
        return "Global"
    if is_generic_value(text):
        return "Não informado"
    return "Brasil"


def classify_institution_type(value: Any) -> str:
    text = strip_accents_lower(value)
    rules = [
        ("Universidade", ["universidade", "university", "faculdade", "uf", "usp", "unicamp", "unb", "uerj", "ufrj", "ufmg", "uel", "ifro"]),
        ("Governo", ["ministerio", "secretaria", "governo", "prefeitura", "camara", "senado", "municipal", "estadual", "federal", "seplag", "mme", "mapa"]),
        ("Organização Internacional", ["nacoes unidas", "onu", "unesco", "pnud", "oecd", "ocde", "banco mundial", "world bank", "bid", "united nations"]),
        ("Empresa", ["ltda", "s/a", "sa", "empresa", "consultoria", "petrobras", "marsh", "smithery", "cemig"]),
        ("Banco / Fomento", ["bndes", "banco", "bank", "fomento", "kfw"]),
        ("ONG / Sociedade Civil", ["ong", "instituto", "fundacao", "associacao", "rede", "movimento", "observatorio", "quilombo"]),
        ("Think Tank / Pesquisa", ["ipea", "centro de estudos", "grupo de economia", "laboratorio", "plataforma"]),
    ]
    for tipo, keywords in rules:
        if _match(text, keywords):
            return tipo
    return "Outro"


def classify_institution_origin(value: Any) -> str:
    text = strip_accents_lower(value)
    if _match(text, ["united nations", "nacoes unidas", "unesco", "pnud", "oecd", "ocde", "world bank", "bid", "kfw", "city university of new york"]):
        return "Multinacional"
    if _match(text, ["france", "ireland", "university", "bankengruppe", "marsh mclennan"]):
        return "Estrangeira"
    if _match(text, ["prefeitura", "municipal", "cidade", "fortaleza", "recife", "belo horizonte"]):
        return "Municipal"
    if _match(text, ["estado", "estadual", "seplag", "governo do estado", "sima/sp", "cemig"]):
        return "Estadual"
    if _match(text, ["ministerio", "federal", "nacional", "bndes", "embrapa", "ipea", "senado"]):
        return "Nacional"
    return "Nacional"


def classify_condition_category(value: Any) -> str:
    text = strip_accents_lower(value)
    rules = [
        ("Ambiental", ["clima", "ambient", "desmat", "floresta", "carbon", "emisso", "biodivers", "agua", "residuo", "ecossistema", "poluicao", "recursos naturais", "solo", "energia"]),
        ("Social", ["pobreza", "fome", "desigual", "educacao", "saude", "genero", "violencia", "habitacao", "emprego", "renda", "demograf", "populacao", "migra"]),
        ("Econômico", ["econom", "fiscal", "credito", "financiamento", "produtiv", "mercado", "investimento", "cadeia produtiva", "juros", "capital", "demanda", "producao", "crescimento", "competitiv", "comercio"]),
        ("Tecnológico", ["tecnolog", "digital", "inovacao", "dados", "inteligencia artificial", "automacao", "pesquisa", "conhecimento"]),
        ("Político", ["politic", "governo", "conflito", "democr", "eleitoral", "regulatorio", "regulacao", "geopolit", "seguranca"]),
        ("Institucional", ["institu", "gestao", "governanca", "capacidade", "planejamento", "coordenacao", "monitoramento", "incerteza", "complexidade", "risco", "mudanca", "cenario", "tendencia", "transformacao"]),
    ]
    for category, keywords in rules:
        if _match(text, keywords):
            return category
    return "Outros"


def classify_condition_cluster(value: Any) -> str:
    text = strip_accents_lower(value)
    rules = [
        ("Mudanças climáticas e transição ambiental", ["clima", "carbon", "emisso", "desmat", "floresta", "ambient"]),
        ("Recursos naturais e biodiversidade", ["biodivers", "ecossistema", "agua", "recursos hidricos", "miner", "solo"]),
        ("Desigualdade e vulnerabilidade social", ["pobreza", "fome", "desigual", "violencia", "habitacao", "saude", "educacao"]),
        ("Conjuntura econômica e financiamento", ["econom", "fiscal", "credito", "financiamento", "juros", "mercado", "investimento"]),
        ("Tecnologia e inovação", ["tecnolog", "digital", "inovacao", "dados", "inteligencia artificial"]),
        ("Governança e capacidade institucional", ["institu", "gestao", "governanca", "planejamento", "coordenacao", "capacidade"]),
        ("Riscos políticos e regulatórios", ["politic", "regulatorio", "regulacao", "conflito", "democr"]),
        ("Demanda, produção e cadeias produtivas", ["demanda", "producao", "cadeia produtiva", "alimento", "energia"]),
    ]
    for cluster, keywords in rules:
        if _match(text, keywords):
            return cluster
    return "Outros condicionantes"


def quality_level(score: float) -> str:
    if score >= 0.80:
        return "Alta"
    if score >= 0.55:
        return "Média"
    if score >= 0.35:
        return "Baixa"
    return "Crítica"
