from __future__ import annotations

import re
import unicodedata
from typing import Any

MISSING_VALUES = {"", "nao informado", "não informado", "nao identificado", "não identificado", "none", "nan", "null"}

def norm_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip().lower()

def _contains(text: str, *patterns: str) -> bool:
    return any(p in text for p in patterns)

def _row_institution(raw: str, tipo: str, origem: str, nivel: str = "Não se aplica", escopo: str = "Não identificado", confianca: str = "alta", acao: str = "aplicar_automatico", justificativa: str = "Classificação por regra determinística.") -> dict[str, Any]:
    return {
        "valor_original": raw,
        "tipo_instituicao": tipo,
        "origem_instituicao": origem,
        "nivel_governamental": nivel,
        "pais_ou_escopo": escopo,
        "confianca": confianca,
        "acao_recomendada": acao,
        "fonte_classificacao": "regra",
        "qualidade_classificacao": "Alta" if confianca == "alta" else "Média",
        "justificativa": justificativa,
    }

def classify_institution_rule(value: str) -> dict[str, Any] | None:
    raw = (value or "").strip()
    text = norm_text(raw)
    if not text or text in MISSING_VALUES:
        return None

    known_ngo = [
        "article 19", "gestos", "acao educativa", "act promocao", "actionaid", "alianca residuo zero",
        "abong", "ablm", "campanha nacional pelo direito a educacao", "casa fluminense", "climax brasil",
        "engajamundo", "fnpeti", "geledes", "ibase", "iddh", "idec", "ids", "inesc", "instituto polis",
        "instituto 5 elementos", "instituto agua e saneamento", "instituto costa brasilis", "instituto maramar",
        "instituto physis", "movimento nacional", "observatorio de governanca", "observatorio metropolitano",
        "ouvidoria do mar", "oxfam", "plan internacional brasil", "programa cidades sustentaveis", "rebrapd",
        "rede mas", "rede nacional", "the nature conservancy", "transparencia internacional", "visao mundial",
        "vital strategies", "wildlife conservation society", "wwf", "agenda publica", "gt agenda 2030",
        "parceria brasileira", "frente por uma nova politica", "comite de articulacao", "oceano a vista",
        "albm", "forum de ongs", "febabs", "febab",
    ]
    if any(k in text for k in known_ngo):
        tipo = "Rede/Coalizão" if _contains(text, "rede", "coalizao", "coalizão", "forum", "frente", "comite", "campanha", "gt ") else "ONG / Sociedade Civil"
        origem = "Nacional"
        if _contains(text, "international", "internacional") and not _contains(text, "brasil"):
            origem = "Internacional"
        return _row_institution(raw, tipo, origem, escopo="Brasil" if origem == "Nacional" else "Internacional", justificativa="Nome conhecido ou padrão de organização da sociedade civil/rede.")

    university_acronyms = ["usp", "ufrj", "ufpr", "unb", "upe", "uerj", "univali", "uema", "ufgd", "unifesp", "ufmg", "ufba", "ufpe", "ufsc", "ufscar", "ufabc", "puc", "unicamp", "unesp"]
    if (_contains(text, "universidade", "university", "faculdade", "college", "programa interunidades de pos-graduacao", "pós-graduação")
        or any(re.search(rf"\b{re.escape(sigla)}\b", text) for sigla in university_acronyms)
        or re.search(r"\buf[a-z]{1,5}\b", text) or re.search(r"\bue[a-z]{1,5}\b", text)):
        origem, nivel, escopo = "Não identificado", "Não identificado", "Não identificado"
        if _contains(text, "universidade federal") or re.search(r"\buf[a-z]{1,5}\b", text) or any(sigla in text for sigla in ["ufrj", "ufpr", "ufgd", "unifesp", "unb", "ufmg", "ufba", "ufpe", "ufsc", "ufscar", "ufabc"]):
            origem, nivel, escopo = "Nacional", "Federal", "Brasil"
        elif _contains(text, "universidade estadual") or re.search(r"\bue[a-z]{1,5}\b", text) or any(sigla in text for sigla in ["usp", "uerj", "upe", "uema", "unicamp", "unesp"]):
            origem, nivel, escopo = "Estadual", "Estadual", "Brasil"
        elif _contains(text, "university college", "college cork", "university of", "college"):
            origem, nivel, escopo = "Estrangeira", "Não se aplica", "Estrangeiro"
        return _row_institution(raw, "Universidade", origem, nivel, escopo, justificativa="Nome indica universidade, faculdade ou unidade acadêmica.")

    gov_patterns = ["ministerio", "ministry", "secretaria", "prefeitura", "governo", "senado", "camara", "câmara", "ibge", "ipea", "fundaj", "fundacao joaquim nabuco", "portal da transparencia", "agencia nacional", "autarquia", "tribunal", "stf", "planalto"]
    if _contains(text, *gov_patterns):
        origem, nivel = "Nacional", "Federal"
        if _contains(text, "prefeitura", "municipal"):
            origem, nivel = "Municipal", "Municipal"
        elif _contains(text, "estadual", "estado de"):
            origem, nivel = "Estadual", "Estadual"
        return _row_institution(raw, "Governo", origem, nivel, "Brasil", justificativa="Nome indica órgão público, autarquia, fundação pública ou fonte governamental.")

    international_patterns = ["united nations", "nacoes unidas", "nações unidas", "world bank", "banco mundial", "oecd", "ocde", "cepal", "eclac", "unesco", "undp", "pnud", "who", "oms", "fao", "ipcc", "un news", "international energy initiative", "iei brasil", "onu"]
    if _contains(text, *international_patterns):
        origem = "Internacional" if not _contains(text, "brasil") else "Multinacional"
        return _row_institution(raw, "Organização Internacional", origem, escopo="Internacional/Multilateral", justificativa="Nome indica organismo ou rede internacional/multilateral.")

    if _contains(text, "associacao", "associação", "rede", "coalizao", "coalizão", "coletivo", "movimento", "forum", "fórum", "campanha", "frente", "comite", "comitê"):
        tipo = "Rede/Coalizão" if _contains(text, "rede", "coalizao", "coalizão", "forum", "fórum", "campanha", "frente", "comite", "comitê") else "ONG / Sociedade Civil"
        return _row_institution(raw, tipo, "Nacional", escopo="Brasil", justificativa="Nome indica associação, rede, coalizão, fórum, campanha ou movimento social.")

    if _contains(text, "observatorio", "observatório"):
        return _row_institution(raw, "Observatório / Plataforma", "Nacional", escopo="Brasil", justificativa="Nome indica observatório ou plataforma de acompanhamento.")
    if _contains(text, "laboratorio", "laboratório"):
        if _contains(text, "unifesp", "ufrj", "usp", "ufpr", "universidade"):
            origem = "Nacional" if _contains(text, "uf", "unifesp", "ufrj", "ufpr") else "Estadual"
            nivel = "Federal" if origem == "Nacional" else "Estadual"
            return _row_institution(raw, "Universidade", origem, nivel, "Brasil", justificativa="Laboratório vinculado a universidade.")
        return _row_institution(raw, "Instituto de Pesquisa", "Nacional", escopo="Brasil", confianca="media", justificativa="Nome indica laboratório ou centro técnico/científico.")
    if _contains(text, "instituto", "institute", "centro", "center", "centre"):
        tipo = "Instituto de Pesquisa"
        if _contains(text, "politicas publicas", "políticas públicas", "desenvolvimento", "socioeconomico", "socioeconômico", "democracia", "sustentabilidade", "governanca"):
            tipo = "Think Tank"
        if _contains(text, "mulher negra", "defesa do consumidor", "direitos humanos", "cultura", "ambiente"):
            tipo = "ONG / Sociedade Civil"
        origem = "Internacional" if _contains(text, "international", "global") else "Nacional"
        return _row_institution(raw, tipo, origem, escopo="Brasil" if origem == "Nacional" else "Internacional", confianca="media", justificativa="Nome indica instituto, centro ou entidade técnica.")

    if _contains(text, "fundacao", "fundação", "foundation"):
        origem = "Nacional" if not _contains(text, "international", "global") else "Internacional"
        return _row_institution(raw, "Fundação", origem, escopo="Brasil" if origem == "Nacional" else "Internacional", confianca="media", justificativa="Nome indica fundação.")
    if _contains(text, "programa", "program", "iniciativa", "initiative"):
        return _row_institution(raw, "Programa / Iniciativa", "Nacional", escopo="Brasil", confianca="media", justificativa="Nome indica programa ou iniciativa institucional.")
    if _contains(text, " ltda", " s.a", " s/a", " inc", " llc", "company", "consultoria", "consulting", "starling", "editora"):
        return _row_institution(raw, "Empresa", "Não identificado", "Não se aplica", "Não identificado", confianca="media", acao="revisar_manual", justificativa="Nome sugere empresa, editora, consultoria ou organização privada.")
    return None

def classify_method_rule(value: str) -> dict[str, Any] | None:
    raw = (value or "").strip(); text = norm_text(raw)
    if not text or text in MISSING_VALUES: return None
    def row(codfam, fam, codsub, sub, natureza, funcao, grau, conf="alta", acao="aplicar_automatico", just="Classificação por palavra-chave.", normalizado: str | None = None):
        return {"valor_original": raw, "valor_normalizado": normalizado or raw, "codigo_familia": codfam, "familia_metodo": fam, "codigo_subfamilia": codsub, "subfamilia_metodo": sub, "natureza_metodo": natureza, "funcao_primaria": funcao, "grau_prospectivo": grau, "confianca": conf, "acao_recomendada": acao, "fonte_classificacao": "regra", "qualidade_classificacao": "Alta" if conf == "alta" else "Média", "justificativa": just}
    if _contains(text, "delphi", "consulta a especialista", "consulta estruturada", "especialistas"): return row("E", "Métodos Participativos e Colaborativos", "E1", "Consultas Estruturadas", "Qualitativa / Criativa", "Mobilizar inteligência coletiva", "Alto", normalizado="Consulta a especialistas / Delphi")
    if _contains(text, "workshop", "oficina", "grupo focal", "grupos focais", "focus group", "brainstorm", "dinamica de grupo", "dinâmica de grupo"): return row("E", "Métodos Participativos e Colaborativos", "E2", "Dinâmicas de Grupo", "Qualitativa / Criativa", "Mobilizar inteligência coletiva", "Médio", normalizado="Oficinas / grupos focais")
    if _contains(text, "cenario", "cenário", "cenarios", "cenários", "scenario", "foresight", "futures thinking", "strategic foresight"): return row("A", "Métodos Exploratórios-Qualitativos", "A1", "Construção de Futuros Alternativos", "Qualitativa / Criativa", "Explorar futuros alternativos", "Alto", normalizado="Construção de cenários")
    if _contains(text, "backcasting", "visao de futuro", "visão de futuro", "future vision", "three horizons", "roadmap"): return row("A", "Métodos Exploratórios-Qualitativos", "A2", "Futuros Normativos / Backcasting", "Qualitativa / Criativa", "Explorar futuros desejáveis e trajetórias de transição", "Alto", normalizado="Visão de futuro / backcasting")
    if _contains(text, "micmac", "impacto cruzado", "impactos cruzados", "cross-impact", "analise morfologica", "análise morfológica", "analise de atores", "abordagem sistemica", "sistêmica", "analise estrutural", "análise estrutural"): return row("A", "Métodos Exploratórios-Qualitativos", "A3", "Análise de Dinâmicas e Estruturas", "Qualitativa / Criativa", "Explorar relações, estruturas e interdependências", "Alto", normalizado="Análise estrutural / sistêmica")
    if _contains(text, "horizon scanning", "environmental scanning", "varredura", "sinal fraco", "weak signal", "wild card", "sinais"): return row("B", "Métodos de Monitoramento e Inteligência", "B1", "Scanning e Vigilância", "Monitoramento / Inteligência", "Capturar sinais do presente", "Alto", normalizado="Horizon scanning / sinais")
    if _contains(text, "tendencia", "tendência", "megatendencia", "megatendência", "trend", "padroes", "padrões"): return row("B", "Métodos de Monitoramento e Inteligência", "B2", "Análise de Padrões", "Monitoramento / Inteligência", "Monitorar padrões e mudanças emergentes", "Médio", normalizado="Análise de tendências")
    if _contains(text, "benchmark", "revisao de literatura", "revisão de literatura", "bibliograf", "referencias externas", "referências externas", "scielo", "capes", "revisao documental", "revisão documental"): return row("B", "Métodos de Monitoramento e Inteligência", "B3", "Benchmarking e Referências", "Monitoramento / Inteligência", "Capturar referências e boas práticas", "Baixo", conf="media", normalizado="Revisão de literatura / benchmarking")
    if _contains(text, "arima", "regress", "serie temporal", "série temporal", "forecast", "extrapola", "projecao estatistica", "projeção estatística", "previsao", "previsão"): return row("C", "Métodos Preditivos-Quantitativos", "C1", "Projeções por Extrapolação", "Quantitativa / Analítica", "Projetar tendências", "Alto", normalizado="Projeção estatística / forecast")
    if _contains(text, "modelo macroeconomico", "macroeconom", "cobb-douglas", "solow", "econometr", "cge", "equilibrio geral", "equilíbrio geral"): return row("C", "Métodos Preditivos-Quantitativos", "C2", "Modelagem Macroeconômica", "Quantitativa / Analítica", "Projetar tendências com modelos econômicos", "Alto", normalizado="Modelagem macroeconômica/econométrica")
    if _contains(text, "monte carlo", "simulacao", "simulação", "otimizacao", "otimização", "sensibilidade"): return row("C", "Métodos Preditivos-Quantitativos", "C3", "Simulação e Otimização", "Quantitativa / Analítica", "Simular incertezas e alternativas", "Alto", normalizado="Simulação / análise de sensibilidade")
    if _contains(text, "iam", "avaliacao integrada", "avaliação integrada", "modelo climatico", "modelo climático", "ipcc", "blues", "globio", "leontief", "insumo-produto", "input-output"): return row("D", "Modelos Integrados e Complexos", "D1", "Modelos de Avaliação Integrada", "Quantitativa / Analítica", "Simular sistemas complexos multidimensionais", "Alto", normalizado="Modelagem integrada / complexa")
    if _contains(text, "swot", "risco", "riscos", "custo-beneficio", "custo benefício", "gap", "lacuna", "diagnostico", "diagnóstico", "viabilidade", "trade-off", "tradeoff", "incerteza critica", "incerteza crítica"): return row("F", "Métodos de Avaliação e Análise de Viabilidade", "F2", "Avaliação Estratégica", "Diagnóstica / Avaliativa", "Avaliar situação atual, riscos e trade-offs", "Médio", normalizado="Avaliação estratégica / análise de riscos")
    if _contains(text, "planejamento estrategico", "planejamento estratégico", "teoria da mudanca", "teoria da mudança", "balanced scorecard", "bsc", "indicador", "indicadores", "monitoramento de indicadores", "monitoramento e avaliacao", "monitoramento e avaliação", "metas", "classificacao de metas", "classificação de metas"): return row("G", "Métodos de Planejamento e Operacionalização", "G3", "Monitoramento e Controle", "Instrumental / Operacional", "Traduzir futuros em monitoramento, metas e controle", "Médio", normalizado="Monitoramento de indicadores/metas")
    if _contains(text, "coleta de dados", "dados oficiais", "analise de dados", "análise de dados", "pesquisa academica", "pesquisa acadêmica", "sistematizacao", "sistematização", "consolidacao", "consolidação", "validacao de texto", "validação de texto", "revisao e correcao", "revisão e correção", "graficos", "gráficos", "elementos visuais"): return row("F", "Métodos de Avaliação e Análise de Viabilidade", "F3", "Pesquisa Qualitativa", "Diagnóstica / Avaliativa", "Fundamentar diagnóstico e avaliação", "Baixo", conf="alta", normalizado="Pesquisa, sistematização e análise de dados", just="Etapa de pesquisa/análise; útil para diagnóstico, mas não é método prospectivo específico.")
    return None

def classify_condition_rule(value: str) -> dict[str, Any] | None:
    raw = (value or "").strip(); text = norm_text(raw)
    if not text or text in MISSING_VALUES: return None
    def row(tipo, steep, cluster, macro, horizonte="Não informado", direcao="Não informado", eh="Sim", conf="media", acao="aplicar_automatico", just="Classificação por palavra-chave."):
        return {"valor_original": raw, "condicionante_normalizado": raw, "tipo_prospectivo": tipo, "categoria_steep": steep, "categoria": steep, "cluster": cluster, "macrocondicionante": macro, "horizonte_implicado": horizonte, "direcionalidade": direcao, "eh_condicionante_prospectivo": eh, "confianca": conf, "acao_recomendada": acao, "fonte_classificacao": "regra", "qualidade_classificacao": "Alta" if conf == "alta" else "Média", "justificativa": just}
    if len(text) < 4 or _contains(text, "copyright", "todos os direitos", "isbn", "disponivel em", "available at", "http", "www.", "lei n", "nota tecnica", "portal", "jornal", "news", "available"):
        return row("Não classificado", "Institucional", "Ruído textual / referência", "Não aplicável", eh="Não", conf="alta", acao="revisar_manual", just="Item parece referência, metadado, norma isolada ou ruído textual, não condicionante prospectivo.")
    if _contains(text, "pandemia", "covid", "crise", "choque", "disruptivo", "guerra", "conflito", "colapso", "emergencia", "emergência"):
        return row("Wild card / Evento disruptivo", "Social", "Choques sistêmicos e eventos disruptivos", "Rupturas e crises", "Curto prazo", "Risco", conf="alta")
    if _contains(text, "mudanca climatica", "mudança climática", "clima", "desmatamento", "degradacao", "degradação", "biodiversidade", "poluicao", "poluição", "emissao", "emissão", "carbono", "agua", "água", "saneamento", "energia", "geleira", "ecossistema", "plastico", "plástico", "residuo", "resíduo"):
        tipo = "Megatendência" if _contains(text, "mudanca climatica", "mudança climática", "clima", "biodiversidade") else "Driver / Força motriz"
        direcao = "Risco" if _contains(text, "risco", "crise", "aumento", "degrad", "desmat", "polu", "derret") else "Ambígua"
        return row(tipo, "Ambiental", "Meio ambiente, clima e recursos naturais", "Transição socioambiental", "Longo prazo", direcao, conf="alta")
    if _contains(text, "desigualdade", "pobreza", "fome", "genero", "gênero", "racial", "racismo", "educacao", "educação", "saude", "saúde", "violencia", "violência", "populacao", "população", "indigena", "indígena", "quilombola", "carceraria", "carcerária", "moradia", "internet", "acesso"):
        return row("Condicionante estrutural", "Social", "Desigualdades, capacidades e direitos", "Coesão social e inclusão", "Médio prazo", "Restrição", conf="alta")
    if _contains(text, "tecnologia", "digital", "inteligencia artificial", "ia", "internet", "dados", "inovacao", "inovação", "automacao", "automação", "ciencia", "ciência"):
        tipo = "Tendência" if not _contains(text, "falta", "ausencia", "ausência", "baixo") else "Driver / Força motriz"
        direcao = "Aceleração" if tipo == "Tendência" else "Restrição"
        return row(tipo, "Tecnológico", "Transformação digital, dados e inovação", "Mudança tecnológica", "Médio prazo", direcao)
    if _contains(text, "econom", "produtividade", "fiscal", "orcamento", "orçamento", "austeridade", "investimento", "capital", "mercado", "emprego", "renda", "financiamento", "desfinanciamento", "teto de gasto", "gastos", "reforma"):
        direcao = "Restrição" if _contains(text, "austeridade", "desfinanciamento", "teto", "fuga", "obstaculo", "obstáculo") else "Ambígua"
        return row("Driver / Força motriz", "Econômico", "Economia, financiamento e produtividade", "Transformação econômica", "Médio prazo", direcao, conf="alta")
    if _contains(text, "governo", "governanca", "governança", "instituicao", "instituição", "politica", "política", "legislativo", "judiciario", "judiciário", "democracia", "corrupcao", "corrupção", "regulacao", "regulação", "comissao", "comissão", "plano plurianual", "ppa", "direitos humanos", "multilateral", "veto", "credibilidade", "conflito entre diferentes niveis", "coordenação"):
        tipo = "Incerteza crítica" if _contains(text, "conflito", "veto", "deslegitim", "credibilidade", "desrespeito") else "Condicionante estrutural"
        return row(tipo, "Institucional", "Governança, capacidades estatais e coordenação", "Governança e instituições", "Médio prazo", "Restrição", conf="alta")
    if _contains(text, "incerteza", "imprevis", "volatil", "volátil", "indefinicao", "indefinição"):
        return row("Incerteza crítica", "Econômico", "Incertezas críticas", "Incerteza e volatilidade", "Não informado", "Ambígua", conf="alta")
    if _contains(text, "falta", "ausencia", "ausência", "lacuna", "obstaculo", "obstáculo", "subnotificacao", "subnotificação", "dados desagregados", "falta de dados"):
        return row("Condicionante estrutural", "Institucional", "Lacunas de informação, capacidades e implementação", "Capacidade institucional e informacional", "Curto prazo", "Restrição", conf="alta")
    return None
