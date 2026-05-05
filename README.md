# PDF Inventory Project — versão final com cache de normalização IA

Pipeline modular para inventariar PDFs técnicos e preparar dados para BI.

## Principais camadas

1. **Extração com LLM**  
   PDFs em `data/01_raw/pdfs` → JSON bruto em `data/02_extracted/json_raw`.

2. **Transformação inicial**  
   JSON bruto → tabelas tratadas, valores únicos e pendências em `data/03_transformed`.

3. **Normalização assistida por IA com cache por lote**  
   Valores únicos → dicionários auditáveis em `data/03_transformed/normalizacao_ia/dicionarios_normalizacao`.

4. **Aplicação dos dicionários**  
   Dicionários aprovados automaticamente → bases normalizadas em `data/03_transformed/normalizacao_ia/bases_normalizadas`.

5. **Enrichment semântico**  
   Instituições e condicionantes → `data/03_transformed/enrichment_ai`.

6. **Preparação para BI**  
   Dados normalizados/enriquecidos → dimensões, fatos e pontes em `data/04_bi_ready`.

## Instalação com uv

```powershell
uv venv --seed
.venv\Scripts\Activate.ps1
uv pip install --link-mode=copy -r requirements.txt
```

## Configuração

```powershell
copy .env.example .env
```

Preencha `GEMINI_API_KEY`.

## Dois modelos

A versão final usa dois modelos configuráveis:

- `MODEL_SIMPLE`: modelo mais simples/barato para chamadas pequenas e rotineiras.
- `MODEL_CONTEXT`: modelo de maior capacidade/contexto para prompts grandes e fallback.

A seleção é automática:

- prompts menores usam `MODEL_SIMPLE`;
- prompts grandes, acima de `CONTEXT_MODEL_MIN_CHARS`, usam `MODEL_CONTEXT`;
- falhas sucessivas também fazem fallback para `MODEL_CONTEXT`.

## Cache/checkpoint da normalização IA

A normalização por IA agora salva cache por lote em:

```text
data/03_transformed/normalizacao_ia/cache_lotes
```

E controle em:

```text
data/03_transformed/normalizacao_ia/controle_processamento/controle_normalizacao_ia.csv
```

Se o processo parar no meio da normalização, rode novamente:

```powershell
python main.py --stage ai-normalization --only-new-values
```

O pipeline reaproveita:

- dicionários já gerados;
- lotes já processados;
- cache de lote salvo.

## Execução recomendada para lote grande

Evite `--stage all` para inventário grande. Rode em etapas:

```powershell
python main.py --stage extraction
python main.py --stage retry-failed
python main.py --stage transformation
python main.py --stage ai-normalization --only-new-values
python main.py --stage apply-normalization
python main.py --stage enrichment
python main.py --stage bi
```

## Extração em lotes

```powershell
python main.py --stage extraction --offset 0 --limit 25
python main.py --stage extraction --offset 25 --limit 25
python main.py --stage extraction --offset 50 --limit 25
```

## Normalização por alvos específicos

```powershell
python main.py --stage ai-normalization --targets setor,tipo_documento,temas --only-new-values
```

## Enrichment

```powershell
python main.py --stage enrichment
python main.py --stage bi
```

O enrichment gera:

- `dicionario_instituicoes_enriquecido.csv`
- `dicionario_condicionantes_cluster.csv`

## BI

A camada BI usa preferencialmente a base normalizada por IA, quando existir:

```text
data/03_transformed/normalizacao_ia/bases_normalizadas/documentos_consolidados_normalizado_ia.csv
```

E exporta:

- dimensões em `data/04_bi_ready/dimensoes`
- fatos em `data/04_bi_ready/fatos`
- pontes em `data/04_bi_ready/pontes`

## Atualização v9 — semântica prospectiva

Esta versão adiciona enriquecimento semântico específico para estudos de futuro:

- métodos classificados segundo taxonomia A–G:
  - A Métodos Exploratórios-Qualitativos
  - B Métodos de Monitoramento e Inteligência
  - C Métodos Preditivos-Quantitativos
  - D Modelos Integrados e Complexos
  - E Métodos Participativos e Colaborativos
  - F Métodos de Avaliação e Análise de Viabilidade
  - G Métodos de Planejamento e Operacionalização
- condicionantes classificados como elementos prospectivos:
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
- condicionantes também recebem classificação STEEP+I.

Para atualizar as dimensões semânticas, rode:

```powershell
python main.py --stage transformation
python main.py --stage enrichment
python main.py --stage bi
```

Se já houver extração e normalização aplicadas, basta rodar:

```powershell
python main.py --stage enrichment
python main.py --stage bi
```

## v11 — refinamento semântico forte

Esta versão reforça a camada de enriquecimento híbrido antes da IA, com foco em reduzir `Não classificado` no BI:

- regras determinísticas ampliadas para instituições de apoio e responsáveis;
- detecção mais robusta de universidades, governo, organismos internacionais, ONGs, redes, fundações, institutos, observatórios, programas e empresas;
- classificação de métodos com taxonomia A–G mais forte antes da IA;
- classificação de condicionantes com tipo prospectivo, STEEP+I, macrocondicionante, horizonte, direcionalidade e filtro de ruído;
- melhoria dos macrotemas e subtemas usados na `dim_tema`;
- merges de enriquecimento por chave normalizada, reduzindo falhas por acentos, caixa alta/baixa e pequenas variações textuais.

Para aplicar em dados já processados:

```powershell
python main.py --stage enrichment
python main.py --stage bi
```

Se quiser reaproveitar normalização anterior e reduzir custo:

```powershell
python main.py --stage ai-normalization --only-new-values
python main.py --stage apply-normalization
python main.py --stage enrichment
python main.py --stage bi
```

## v12 — Normalização de nomes de documentos

Esta versão adiciona governança de nomes de documentos:

- `nome_documento`: título original extraído, preservado para auditoria;
- `nome_documento_norm`: título limpo e padronizado para análise;
- `nome_documento_curto`: título reduzido para gráficos, cartões e tabelas no Power BI.

Também mantém a correção da FK direta da instituição responsável na fato:

- `fato_inventario[sk_instituicao]` → `dim_instituicao_responsavel[sk_instituicao]`.

Para aplicar aos dados já extraídos, rode:

```powershell
python main.py --stage transformation
python main.py --stage ai-normalization --only-new-values
python main.py --stage apply-normalization
python main.py --stage enrichment
python main.py --stage bi
```
