# Manual de relacionamentos Power BI

Este manual descreve como relacionar as tabelas geradas em `data/04_bi_ready` no Power BI. A camada segue um modelo estrela com uma fato principal, dimensões diretas e tabelas ponte para relações muitos-para-muitos no nível do documento.

## Tabela fato

Tabela: `fato_inventario.csv`

Grão: uma linha por documento lógico inventariado.

Chave primária técnica:

- `sk_fato_inventario`

Chaves estrangeiras diretas:

- `sk_documento`
- `sk_tempo`
- `sk_setor`
- `sk_abrangencia`
- `sk_metodologia`
- `sk_qualidade`

Campos analíticos principais:

- `aplicou_estudo_futuro`
- `qtd_temas`
- `qtd_metodos`
- `qtd_referencias`
- `qtd_condicionantes`
- `qtd_instituicoes_apoio`
- `densidade_informacional`
- `possui_condicionantes`
- `possui_metodo_identificado`
- `possui_horizonte_temporal`
- `score_qualidade`
- `nivel_qualidade`
- `flag_revisao_manual`

## Relacionamentos diretos

Configure estes relacionamentos como **muitos para um** da fato para a dimensão, com direção de filtro **single** da dimensão para a fato.

| De | Para | Cardinalidade | Observação |
| --- | --- | --- | --- |
| `fato_inventario[sk_documento]` | `dim_documento[sk_documento]` | Muitos para um | Documento principal |
| `fato_inventario[sk_tempo]` | `dim_tempo[sk_tempo]` | Muitos para um | Pode haver documentos sem tempo completo |
| `fato_inventario[sk_setor]` | `dim_setor[sk_setor]` | Muitos para um | Use `macro_setor` para análise agregada |
| `fato_inventario[sk_abrangencia]` | `dim_abrangencia[sk_abrangencia]` | Muitos para um | Use `nivel_abrangencia` e `pais` como hierarquia |
| `fato_inventario[sk_metodologia]` | `dim_metodologia[sk_metodologia]` | Muitos para um | Classificação metodológica consolidada |
| `fato_inventario[sk_qualidade]` | `dim_qualidade[sk_qualidade]` | Muitos para um | Indicadores de qualidade e revisão |

## Pontes documentais

As tabelas ponte conectam `dim_documento` a dimensões multivalor. Configure como:

1. `dim_documento` -> tabela ponte: **um para muitos**.
2. dimensão de destino -> tabela ponte: **um para muitos**.
3. Direção de filtro preferencial: **single**, partindo das dimensões para as pontes.

Evite criar relacionamento direto entre a fato e dimensões multivalor como tema, método, referência, condicionante, apoio ou arquivo de origem. O caminho recomendado passa por `dim_documento`.

## Relacionamentos por ponte

### Temas

| De | Para | Cardinalidade |
| --- | --- | --- |
| `dim_documento[sk_documento]` | `ponte_documento_tema[sk_documento]` | Um para muitos |
| `dim_tema[sk_tema]` | `ponte_documento_tema[sk_tema]` | Um para muitos |

Hierarquia recomendada:

- `dim_tema[macrotema]`
- `dim_tema[subtema]`
- `dim_tema[tema]`

### Métodos

| De | Para | Cardinalidade |
| --- | --- | --- |
| `dim_documento[sk_documento]` | `ponte_documento_metodo[sk_documento]` | Um para muitos |
| `dim_metodo[sk_metodo]` | `ponte_documento_metodo[sk_metodo]` | Um para muitos |

Hierarquia recomendada:

- `dim_metodo[natureza_metodo]`
- `dim_metodo[familia_do_metodo]`
- `dim_metodo[metodo]`

### Instituições de apoio

| De | Para | Cardinalidade |
| --- | --- | --- |
| `dim_documento[sk_documento]` | `ponte_documento_instituicao_apoio[sk_documento]` | Um para muitos |
| `dim_apoio[sk_instituicao_apoio]` | `ponte_documento_instituicao_apoio[sk_instituicao_apoio]` | Um para muitos |

Campos úteis:

- `dim_apoio[tipo_instituicao]`
- `dim_apoio[origem_instituicao]`
- `dim_apoio[instituicao_apoio]`

### Referências

| De | Para | Cardinalidade |
| --- | --- | --- |
| `dim_documento[sk_documento]` | `ponte_documento_referencia[sk_documento]` | Um para muitos |
| `dim_referencia[sk_referencia]` | `ponte_documento_referencia[sk_referencia]` | Um para muitos |

### Condicionantes

| De | Para | Cardinalidade |
| --- | --- | --- |
| `dim_documento[sk_documento]` | `ponte_documento_condicionante[sk_documento]` | Um para muitos |
| `dim_condicionante[sk_condicionante]` | `ponte_documento_condicionante[sk_condicionante]` | Um para muitos |

Hierarquia recomendada:

- `dim_condicionante[categoria]`
- `dim_condicionante[cluster]`
- `dim_condicionante[condicionante]`

### Arquivos de origem

| De | Para | Cardinalidade |
| --- | --- | --- |
| `dim_documento[sk_documento]` | `ponte_documento_arquivo_origem[sk_documento]` | Um para muitos |
| `dim_source_file[sk_source_file]` | `ponte_documento_arquivo_origem[sk_source_file]` | Um para muitos |

Uso recomendado:

- auditoria de origem;
- conferência de rastreabilidade entre documento lógico e PDF original.

## Dimensões sem relacionamento direto recomendado

`dim_instituicao_responsavel` pode ser usada como dimensão auxiliar, mas hoje a relação principal da instituição responsável está dentro de `dim_documento[instituicao_responsavel]`.

Opções:

- Para análises simples, use `dim_documento[instituicao_responsavel]`.
- Para análises por `tipo_instituicao` e `origem_instituicao`, crie relacionamento entre `dim_documento[instituicao_responsavel]` e `dim_instituicao_responsavel[instituicao]`.
- Se criar esse relacionamento por texto, mantenha cardinalidade muitos para um e valide duplicidades em `dim_instituicao_responsavel[instituicao]`.

## Cuidados de modelagem

- Prefira medidas baseadas em `DISTINCTCOUNT(fato_inventario[id_documento_logico])`.
- Em visuais com temas, métodos, condicionantes, referências ou apoio, conte documentos pela ponte usando `DISTINCTCOUNT(ponte_...[sk_documento])`.
- Evite bidirecionalidade global. Use direção de filtro single e medidas DAX específicas quando precisar atravessar pontes.
- `sk_tempo` pode ter nulos quando `ano_publicacao`, `horizonte_temporal` ou `extensao_tempo` não formarem uma combinação válida.
- `extensao_tempo` negativa deve ser tratada como alerta de qualidade, não como horizonte válido.

## Checklist de conferência

- `fato_inventario[sk_documento]` sem nulos.
- `fato_inventario[sk_qualidade]` sem nulos.
- `dim_documento[sk_documento]` única.
- Todas as `sk_*` nas pontes sem nulos.
- `dim_source_file` com linhas após rodar `transformation` e `bi`.
- Contagem esperada: `DISTINCTCOUNT(fato_inventario[id_documento_logico])` igual ao número de linhas da fato.
