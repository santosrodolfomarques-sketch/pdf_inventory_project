from __future__ import annotations


def build_extraction_prompt(texto_pdf: str) -> str:
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
5. Não classifique métodos em família; apenas extraia os métodos mencionados.
6. Só marque "aplicou_estudo_futuro" como true quando houver evidência de prospectiva, cenários, projeções, modelagem, foresight, backcasting, Delphi ou método análogo. Ter um ano no título, como 2030 ou 2050, por si só não basta.
7. Quando houver apenas visão aspiracional, reflexão, ensaio ou discussão geral sobre futuro, prefira false ou null.
8. Em "instituicao_responsavel", priorize a instituição autora, coordenadora ou responsável intelectual pelo documento. Não confunda automaticamente editora, selo editorial ou gráfica com autoria institucional.

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
  "referencias": [],
  "condicionantes_estudo_futuro": [],
  "instituicoes_apoio": [],
  "instituicao_responsavel": null
}}

TEXTO DO DOCUMENTO:
{texto_pdf}
""".strip()
