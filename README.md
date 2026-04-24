# PDF Inventory Project — versão com normalização assistida por IA

Pipeline modular para inventariar PDFs técnicos e preparar dados para BI.

## Camadas

1. **Extração com LLM**  
   PDFs em `data/01_raw/pdfs` → JSON bruto em `data/02_extracted/json_raw`.

2. **Transformação inicial**  
   JSON bruto → tabelas tratadas, valores únicos e pendências em `data/03_transformed`.

3. **Normalização assistida por IA**  
   Valores únicos → dicionários auditáveis em `data/03_transformed/normalizacao_ia/dicionarios_normalizacao`.

4. **Aplicação dos dicionários**  
   Dicionários aprovados automaticamente → bases normalizadas em `data/03_transformed/normalizacao_ia/bases_normalizadas`.

5. **Preparação para BI**  
   Dados tratados → dimensões, fatos e pontes em `data/04_bi_ready`.

## Instalação com uv

```powershell
uv venv --seed
.venv\Scripts\Activate.ps1
uv pip install --link-mode=copy -r requirements.txt
```

## Configuração

Copie o arquivo de exemplo:

```powershell
copy .env.example .env
```

Preencha `GEMINI_API_KEY`.

## Execução recomendada

```powershell
python main.py --stage extraction --force-reprocess
python main.py --stage transformation
python main.py --stage ai-normalization
python main.py --stage apply-normalization
python main.py --stage bi
```

## Normalização IA por alvos específicos

```powershell
python main.py --stage ai-normalization --targets setor,tipo_documento,temas
```

## Processar apenas valores novos

```powershell
python main.py --stage ai-normalization --only-new-values
```

## Saídas da normalização IA

- `dicionario_setor.csv`
- `dicionario_tipo_documento.csv`
- `dicionario_abrangencia_territorial.csv`
- `dicionario_tipo_estudo_futuro.csv`
- `dicionario_familia_do_metodo.csv`
- `dicionario_temas.csv`
- `dicionario_metodos.csv`
- `dicionario_instituicoes.csv`

Cada dicionário contém:

- `valor_original`
- `valor_normalizado`
- `categoria`
- `confianca`
- `acao_recomendada`
- `justificativa`
- `aplicar_automaticamente`

A IA não altera a base diretamente. A aplicação dos dicionários usa apenas linhas marcadas como `aplicar_automaticamente = True`.

## Camada BI otimizada

Esta versão inclui uma camada BI semântica em `src/bi` com:

- uso prioritário de colunas normalizadas (`*_norm`) quando existirem;
- hierarquia temática: `macrotema -> subtema -> tema`;
- hierarquia metodológica: `natureza_metodologia -> familia_do_metodo -> tipo_estudo_futuro`;
- dimensão de qualidade (`dim_qualidade`) com score, nível e motivos de revisão;
- fato enriquecida com flags e contagens analíticas;
- medidas DAX sugeridas em `docs/medidas_powerbi_sugeridas.md`.

Sequência recomendada:

```powershell
python main.py --stage transformation
python main.py --stage ai-normalization
python main.py --stage apply-normalization
python main.py --stage bi
```

Se a normalização IA ainda não tiver sido aplicada, o BI usa a base consolidada comum como fallback.
