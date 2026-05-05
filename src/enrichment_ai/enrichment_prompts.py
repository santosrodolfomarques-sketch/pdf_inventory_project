from __future__ import annotations

import json

TAXONOMIA_METODOS_FUTURO = {
    "A": {
        "familia": "Métodos Exploratórios-Qualitativos",
        "funcao": "Explorar futuros alternativos",
        "natureza": "Qualitativa / Criativa",
        "subfamilias": {
            "A1": "Construção de Futuros Alternativos",
            "A2": "Futuros Normativos / Backcasting",
            "A3": "Análise de Dinâmicas e Estruturas",
        },
        "exemplos": [
            "Construção de Cenários", "Strategic Foresight", "Futures Thinking",
            "Visão de Futuro", "Backcasting", "Three Horizons", "Análise Estrutural",
            "MICMAC", "Análise de Impactos Cruzados", "Análise Morfológica",
            "Análise de Atores", "Abordagem Sistêmica",
        ],
    },
    "B": {
        "familia": "Métodos de Monitoramento e Inteligência",
        "funcao": "Capturar sinais do presente",
        "natureza": "Monitoramento / Inteligência",
        "subfamilias": {
            "B1": "Scanning e Vigilância",
            "B2": "Análise de Padrões",
            "B3": "Benchmarking e Referências",
        },
        "exemplos": [
            "Horizon Scanning", "Weak Signals", "Wild Cards", "Análise de Tendências",
            "Megatendências", "Benchmarking", "Revisão de Literatura",
        ],
    },
    "C": {
        "familia": "Métodos Preditivos-Quantitativos",
        "funcao": "Projetar tendências",
        "natureza": "Quantitativa / Analítica",
        "subfamilias": {
            "C1": "Projeções por Extrapolação",
            "C2": "Modelagem Macroeconômica",
            "C3": "Simulação e Otimização",
        },
        "exemplos": [
            "Projeções Estatísticas", "Séries Temporais", "Forecast", "Modelagem Econométrica",
            "ARIMA", "Regressão", "Modelos de Crescimento", "Monte Carlo",
            "Análise de Sensibilidade",
        ],
    },
    "D": {
        "familia": "Modelos Integrados e Complexos",
        "funcao": "Simular sistemas complexos multidimensionais",
        "natureza": "Quantitativa / Analítica",
        "subfamilias": {
            "D1": "Modelos de Avaliação Integrada",
            "D2": "Modelos Econômicos de Equilíbrio",
            "D3": "Modelos Específicos Setoriais",
        },
        "exemplos": [
            "IAM", "Modelagem Integrada", "Modelos Climáticos", "CGE", "Leontief",
            "Modelos BLUES", "GLOBIO", "Modelos Energia", "Modelos Agricultura",
            "Bioeconomia",
        ],
    },
    "E": {
        "familia": "Métodos Participativos e Colaborativos",
        "funcao": "Mobilizar inteligência coletiva",
        "natureza": "Qualitativa / Criativa",
        "subfamilias": {
            "E1": "Consultas Estruturadas",
            "E2": "Dinâmicas de Grupo",
            "E3": "Métodos Criativos e Imersivos",
        },
        "exemplos": [
            "Delphi", "Consulta a Especialistas", "Oficinas", "Workshops",
            "Brainstorming", "Grupos Focais", "Artefatos de Futuro", "Redes de Exploradores",
        ],
    },
    "F": {
        "familia": "Métodos de Avaliação e Análise de Viabilidade",
        "funcao": "Avaliar situação atual, riscos e trade-offs",
        "natureza": "Diagnóstica / Avaliativa",
        "subfamilias": {
            "F1": "Diagnóstico e Gap Analysis",
            "F2": "Avaliação Estratégica",
            "F3": "Pesquisa Qualitativa",
        },
        "exemplos": [
            "Diagnóstico Situacional", "Identificação de Lacunas", "Análise de Incertezas Críticas",
            "SWOT", "Análise de Riscos", "Custo-Benefício", "Pesquisa Qualitativa",
        ],
    },
    "G": {
        "familia": "Métodos de Planejamento e Operacionalização",
        "funcao": "Traduzir futuros em planos de ação",
        "natureza": "Instrumental / Operacional",
        "subfamilias": {
            "G1": "Planejamento Estratégico",
            "G2": "Frameworks de Transição",
            "G3": "Monitoramento e Controle",
        },
        "exemplos": [
            "Planejamento Estratégico", "Teoria da Mudança", "Balanced Scorecard",
            "Three Horizons", "Modelo Donut", "Monitoramento de Indicadores",
        ],
    },
}


def build_institution_enrichment_prompt(valores: list[str]) -> str:
    values_json = json.dumps(valores, ensure_ascii=False, indent=2)
    return f"""
Você é um assistente especialista em classificação institucional para análise de políticas públicas e planejamento de longo prazo.

Classifique cada instituição abaixo.

Para cada item, retorne:
- valor_original: exatamente como recebido
- tipo_instituicao: uma entre Universidade, Governo, ONG, Think Tank, Empresa, Organização Internacional, Fundação, Rede/Coalizão, Instituto de Pesquisa, Outro
- origem_instituicao: uma entre Municipal, Estadual, Nacional, Estrangeira, Multinacional, Internacional, Outro, Não identificado
- confianca: alta, media ou baixa
- justificativa: curta

Regras:
1. Não invente. Quando não houver evidência suficiente, use "Não identificado" e confiança baixa.
2. Universidades estaduais brasileiras devem ser "Universidade" e origem "Estadual".
3. Universidades federais brasileiras devem ser "Universidade" e origem "Nacional".
4. Organismos como ONU, Banco Mundial, OCDE, CEPAL e similares devem ser "Organização Internacional".
5. ONGs, redes da sociedade civil e coletivos devem ser classificados como "ONG" ou "Rede/Coalizão".

Retorne APENAS JSON válido no formato:
{{
  "items": [
    {{
      "valor_original": "...",
      "tipo_instituicao": "...",
      "origem_instituicao": "...",
      "confianca": "alta|media|baixa",
      "justificativa": "..."
    }}
  ]
}}

INSTITUIÇÕES:
{values_json}
""".strip()


def build_method_taxonomy_prompt(valores: list[str]) -> str:
    values_json = json.dumps(valores, ensure_ascii=False, indent=2)
    taxonomy_json = json.dumps(TAXONOMIA_METODOS_FUTURO, ensure_ascii=False, indent=2)
    return f"""
Você é especialista em prospectiva estratégica, foresight, estudos de futuro e taxonomias de métodos.

Classifique cada método abaixo usando OBRIGATORIAMENTE a taxonomia hierárquica de métodos de estudos de futuro.

TAXONOMIA CONTROLADA:
{taxonomy_json}

FAMÍLIAS PERMITIDAS:
A - Métodos Exploratórios-Qualitativos
B - Métodos de Monitoramento e Inteligência
C - Métodos Preditivos-Quantitativos
D - Modelos Integrados e Complexos
E - Métodos Participativos e Colaborativos
F - Métodos de Avaliação e Análise de Viabilidade
G - Métodos de Planejamento e Operacionalização

SUBFAMÍLIAS PERMITIDAS:
A1 - Construção de Futuros Alternativos
A2 - Futuros Normativos / Backcasting
A3 - Análise de Dinâmicas e Estruturas
B1 - Scanning e Vigilância
B2 - Análise de Padrões
B3 - Benchmarking e Referências
C1 - Projeções por Extrapolação
C2 - Modelagem Macroeconômica
C3 - Simulação e Otimização
D1 - Modelos de Avaliação Integrada
D2 - Modelos Econômicos de Equilíbrio
D3 - Modelos Específicos Setoriais
E1 - Consultas Estruturadas
E2 - Dinâmicas de Grupo
E3 - Métodos Criativos e Imersivos
F1 - Diagnóstico e Gap Analysis
F2 - Avaliação Estratégica
F3 - Pesquisa Qualitativa
G1 - Planejamento Estratégico
G2 - Frameworks de Transição
G3 - Monitoramento e Controle

Para cada método, retorne:
- valor_original: exatamente como recebido
- valor_normalizado: forma curta e padronizada do método
- codigo_familia: A, B, C, D, E, F ou G
- familia_metodo: nome completo da família permitida
- codigo_subfamilia: código permitido, ou "Não classificado"
- subfamilia_metodo: nome da subfamília permitida, ou "Não classificado"
- natureza_metodo: Qualitativa / Criativa, Quantitativa / Analítica, Diagnóstica / Avaliativa, Instrumental / Operacional, Monitoramento / Inteligência, Híbrida ou Não classificado
- funcao_primaria: função dominante segundo a taxonomia
- grau_prospectivo: Alto, Médio, Baixo ou Não prospectivo
- confianca: alta, media ou baixa
- acao_recomendada: aplicar_automatico ou revisar_manual
- justificativa: curta

Regras:
1. Não invente método que não esteja sugerido pelo valor original.
2. Quando o valor for apenas fonte de dados, referência ou etapa operacional sem método prospectivo claro, use grau_prospectivo "Baixo" ou "Não prospectivo" e confiança média/baixa.
3. Use E para consultas, oficinas, Delphi, grupos focais e métodos participativos.
4. Use B para scanning, sinais, tendências, megatendências, benchmarking e revisão de literatura quando usados para inteligência prospectiva.
5. Use C/D apenas quando houver projeção, modelo, simulação ou quantificação clara.
6. Use F para diagnóstico, SWOT, riscos, gaps, avaliação de viabilidade e trade-offs.
7. Use G para planejamento, teoria da mudança, indicadores, BSC e operacionalização.

Retorne APENAS JSON válido no formato:
{{
  "items": [
    {{
      "valor_original": "...",
      "valor_normalizado": "...",
      "codigo_familia": "A|B|C|D|E|F|G|Não classificado",
      "familia_metodo": "...",
      "codigo_subfamilia": "...",
      "subfamilia_metodo": "...",
      "natureza_metodo": "...",
      "funcao_primaria": "...",
      "grau_prospectivo": "Alto|Médio|Baixo|Não prospectivo",
      "confianca": "alta|media|baixa",
      "acao_recomendada": "aplicar_automatico|revisar_manual",
      "justificativa": "..."
    }}
  ]
}}

MÉTODOS:
{values_json}
""".strip()


def build_condicionante_prompt(valores: list[str]) -> str:
    values_json = json.dumps(valores, ensure_ascii=False, indent=2)
    return f"""
Você é especialista em prospectiva estratégica e análise de condicionantes de futuro.

Classifique cada condicionante abaixo como elemento de estudos prospectivos, e não apenas como tema setorial.

TIPOS PROSPECTIVOS PERMITIDOS:
- Tendência
- Megatendência
- Driver / Força motriz
- Incerteza crítica
- Sinal fraco
- Wild card / Evento disruptivo
- Risco
- Oportunidade
- Premissa
- Condicionante estrutural
- Fator de contexto
- Não classificado

CATEGORIAS STEEP+I PERMITIDAS:
- Social
- Tecnológico
- Econômico
- Ambiental
- Político
- Institucional

Para cada condicionante, retorne:
- valor_original: exatamente como recebido
- condicionante_normalizado: forma curta e padronizada
- tipo_prospectivo: um dos tipos prospectivos permitidos
- categoria_steep: uma das categorias STEEP+I permitidas
- categoria: mesmo valor de categoria_steep, para compatibilidade com o BI atual
- cluster: rótulo curto e reutilizável, com 2 a 5 palavras
- macrocondicionante: agrupamento mais amplo do cluster
- horizonte_implicado: Curto prazo, Médio prazo, Longo prazo ou Não informado
- direcionalidade: Aceleração, Restrição, Risco, Oportunidade, Ambígua ou Não informado
- confianca: alta, media ou baixa
- acao_recomendada: aplicar_automatico ou revisar_manual
- justificativa: curta

Regras:
1. Não invente informação específica que não esteja no texto.
2. Quando o item for genérico, use "Fator de contexto" ou "Condicionante estrutural".
3. Use "Incerteza crítica" quando houver imprevisibilidade relevante.
4. Use "Sinal fraco" apenas para indícios emergentes ainda incipientes.
5. Use "Megatendência" apenas para processos amplos, estruturais e duradouros.
6. Use "Wild card / Evento disruptivo" apenas para eventos de baixa previsibilidade e alto impacto.
7. Evite criar clusters excessivamente específicos; prefira rótulos reutilizáveis no BI.

Retorne APENAS JSON válido no formato:
{{
  "items": [
    {{
      "valor_original": "...",
      "condicionante_normalizado": "...",
      "tipo_prospectivo": "...",
      "categoria_steep": "...",
      "categoria": "...",
      "cluster": "...",
      "macrocondicionante": "...",
      "horizonte_implicado": "...",
      "direcionalidade": "...",
      "confianca": "alta|media|baixa",
      "acao_recomendada": "aplicar_automatico|revisar_manual",
      "justificativa": "..."
    }}
  ]
}}

CONDICIONANTES:
{values_json}
""".strip()
