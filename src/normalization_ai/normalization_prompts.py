from __future__ import annotations

import json
from typing import Any


TARGET_DESCRIPTIONS = {
    "setor": "setores econômicos, sociais ou institucionais mencionados nos documentos",
    "tipo_documento": "tipos documentais como plano, relatório, estudo, livro, estratégia, policy brief etc.",
    "abrangencia_territorial": "abrangência territorial: nacional, regional, global, estadual, municipal, local etc.",
    "tipo_estudo_futuro": "tipos de estudo de futuro ou abordagem prospectiva identificada",
    "familia_do_metodo": "famílias metodológicas de estudos de futuro",
    "temas": "temas, tópicos e assuntos recorrentes dos documentos",
    "metodos": "métodos, técnicas e procedimentos de análise ou estudos de futuro",
    "instituicoes": "instituições responsáveis, apoiadoras, autoras, editoras ou parceiras",
}


def build_dictionary_prompt(
    *,
    target_name: str,
    values: list[dict[str, Any]],
    allowed_categories: list[str] | None = None,
) -> str:
    """
    Monta um prompt para a LLM propor um dicionário de normalização.

    A LLM não altera a base diretamente; ela apenas propõe um dicionário auditável.
    """
    description = TARGET_DESCRIPTIONS.get(target_name, target_name)
    allowed_text = ""
    if allowed_categories:
        allowed_text = "\nCATEGORIAS CONTROLADAS PERMITIDAS:\n" + json.dumps(
            allowed_categories,
            ensure_ascii=False,
            indent=2,
        )

    values_json = json.dumps(values, ensure_ascii=False, indent=2)

    return f"""
Você é um assistente especialista em curadoria, normalização e categorização de dados documentais para BI.

Sua tarefa é analisar valores únicos de uma base de inventário de documentos e propor um dicionário de normalização.

ALVO DA NORMALIZAÇÃO:
{target_name} — {description}

PRINCÍPIOS:
1. Não invente informação além do que os valores sugerem.
2. Preserve o sentido técnico do valor original.
3. Corrija apenas variações evidentes de grafia, idioma, plural/singular, caixa, abreviação ou tradução.
4. Agrupe sinônimos ou equivalentes semânticos quando houver alta segurança.
5. Quando houver ambiguidade, marque confiança média ou baixa e recomende revisão manual.
6. Não apague valores raros automaticamente se eles forem semanticamente distintos.
7. Para instituições, preserve nomes oficiais quando possível; padronize siglas e variações evidentes.
8. Para temas, prefira nomes curtos, substantivos e reutilizáveis em BI.
9. Para métodos, distinga método, fonte de dados e etapa operacional quando possível.
10. Para família do método, use categorias amplas e consistentes.

SAÍDA OBRIGATÓRIA:
Retorne APENAS um JSON válido com a chave "items".
Cada item deve ter exatamente os campos:
- valor_original: string
- valor_normalizado: string ou null
- categoria: string ou null
- confianca: "alta", "media" ou "baixa"
- acao_recomendada: "aplicar automático", "revisar manualmente" ou "manter original"
- justificativa: string curta

REGRAS PARA AÇÃO:
- Use "aplicar automático" apenas quando a equivalência for segura.
- Use "manter original" quando o valor já estiver adequado.
- Use "revisar manualmente" quando houver ambiguidade, erro provável, sigla obscura ou baixa evidência.

{allowed_text}

VALORES A ANALISAR:
{values_json}
""".strip()
