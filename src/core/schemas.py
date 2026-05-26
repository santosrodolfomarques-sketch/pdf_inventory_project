from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ExtractionModel(BaseModel):
    """Modelo Pydantic rígido para validação do retorno da extração LLM."""
    nome_documento: str | None = Field(
        None,
        description="Nome oficial e completo do documento técnico ou relatório."
    )
    tipo_documento: str | None = Field(
        None,
        description="Tipo de documento. Exemplos: Plano, Estratégia, Relatório, Estudo, Diagnóstico, Livro, Policy Brief."
    )
    ano_publicacao: int | None = Field(
        None,
        description="Ano de publicação do documento (formato YYYY). Deve ser capturado apenas se houver forte evidência."
    )
    horizonte_temporal: int | None = Field(
        None,
        description="Ano alvo projetado no futuro (formato YYYY). Exemplo: no título 'Brasil 2050', o horizonte é 2050."
    )
    abrangencia_territorial: str | None = Field(
        None,
        description="Abrangência espacial: Nacional, Regional, Estadual, Municipal, Global."
    )
    setor: str | None = Field(
        None,
        description="Setor socioeconômico primário do documento. Exemplo: Saúde, Educação, Energia, Transporte, Meio Ambiente."
    )
    temas: list[str] = Field(
        default_factory=list,
        description="Lista de temas chaves, tópicos e assuntos específicos discutidos no documento."
    )
    aplicou_estudo_futuro: bool | None = Field(
        None,
        description="Indica se o documento executou/apresentou estudos de futuro com metodologia estruturada (cenários, Delphi, roadmapping, modelagem, backcasting)."
    )
    tipo_estudo_futuro: str | None = Field(
        None,
        description="Abordagem de futuro identificada. Exemplo: Cenários Prospectivos, Extrapolação de Tendências, Backcasting, Roadmapping."
    )
    metodos_estudo_futuro: list[str] = Field(
        default_factory=list,
        description="Métodos específicos de estudos de futuro ou ferramentas analíticas de prospecção aplicadas."
    )
    referencias: list[str] = Field(
        default_factory=list,
        description="Principais referências bibliográficas, planos anteriores ou fontes citadas no documento."
    )
    condicionantes_estudo_futuro: list[str] = Field(
        default_factory=list,
        description="Fatores de incerteza, condicionantes, gargalos ou forças motrizes que impactam o futuro estudado."
    )
    instituicoes_apoio: list[str] = Field(
        default_factory=list,
        description="Instituições parceiras, financiadoras, apoiadoras ou editoriais mencionadas no documento."
    )
    instituicao_responsavel: str | None = Field(
        None,
        description="Instituição principal autora, coordenadora ou responsável intelectual pelo documento."
    )


class DictionaryItemModel(BaseModel):
    """Modelo Pydantic para um item individual do dicionário de normalização sugerido pela IA."""
    valor_original: str = Field(..., description="O valor original extraído dos documentos técnicos.")
    valor_normalizado: str | None = Field(None, description="O valor padronizado recomendado para a taxonomia unificada de BI.")
    categoria: str | None = Field(None, description="Categoria semântica ampla à qual o valor pertence.")
    confianca: str = Field(..., description="Grau de confiança na equivalência semântica: 'alta', 'media' ou 'baixa'.")
    acao_recomendada: str = Field(
        ...,
        description="Ação sugerida para o pipeline: 'aplicar automático', 'revisar manualmente' ou 'manter original'."
    )
    justificativa: str = Field(..., description="Justificativa lógica da escolha de normalização.")


class DictionaryModel(BaseModel):
    """Modelo de dicionário unificado retornado pela IA normalizadora."""
    items: list[DictionaryItemModel] = Field(..., description="Lote de propostas de normalização recomendadas.")
