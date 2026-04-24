def build_institution_enrichment_prompt(valores):
    return f"""
Classifique cada instituição abaixo.

Para cada uma, retorne:
- valor_original
- tipo_instituicao (Universidade, Governo, ONG, Think Tank, Empresa, Organização Internacional, Outro)
- origem_instituicao (Municipal, Estadual, Nacional, Estrangeira, Multinacional, Outro)
- confianca (alta, media, baixa)

Responda em JSON válido:

[
  {{
    "valor_original": "...",
    "tipo_instituicao": "...",
    "origem_instituicao": "...",
    "confianca": "..."
  }}
]

Instituições:
{valores}
"""

def build_condicionante_prompt(valores):
    return f"""
Agrupe os condicionantes abaixo.

Para cada item, retorne:
- valor_original
- cluster (tema próximo)
- categoria (Ambiental, Social, Econômico, Tecnológico, Político, Institucional)
- confianca

Responda em JSON válido.

Condicionantes:
{valores}
"""