from __future__ import annotations

def build_extraction_prompt(texto_pdf: str, taxonomia_metodos: list[str]) -> str:
    metodos = ", ".join(taxonomia_metodos)

    return f"""
Você é um assistente especializado em extração factual de dados de documentos técnicos.

Sua tarefa é analisar o texto fornecido e devolver APENAS um JSON válido.
Não escreva comentários, explicações ou markdown.
Se uma informação não estiver presente no texto, use null para strings/números e [] para listas.

REGRAS:
1. Extraia apenas o que estiver apoiado pelo texto.
2. Não invente valores.
3. Use ano no formato YYYY quando houver.
4. Para listas, remova duplicações evidentes.
5. "familia_do_metodo" deve ser classificada em UMA das categorias: {metodos}

ESTRUTURA OBRIGATÓRIA:
{{
  "nome_documento": null,
  "tipo_documento": null,
  "ano_publicacao": null,
  "horizonte_temporal": null,
  "abrangencia_territorial": null,
  "setor": null,
  "temas": [],
  "aplicou_estudo_futuro": null,
  "tipo_estudo_futuro": null,
  "metodos_estudo_futuro": [],
  "familia_do_metodo": null,
  "referencias": [],
  "condicionantes_estudo_futuro": [],
  "instituicoes_apoio": [],
  "instituicao_responsavel": null
}}

TEXTO DO DOCUMENTO:
{texto_pdf}
""".strip()
