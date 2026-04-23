# PDF Inventory Reestruturado

Projeto reorganizado em três camadas:

1. **Extração com LLM**
2. **Transformação dos dados**
3. **Preparação para BI**

## Estrutura

```text
data/
  01_raw/pdfs
  02_extracted/json_raw
  02_extracted/logs
  02_extracted/controle_processamento
  03_transformed/tabelas_base
  03_transformed/tabelas_normalizadas
  03_transformed/pendencias
  03_transformed/valores_unicos_para_normalizacao
  04_bi_ready/dimensoes
  04_bi_ready/fatos
  04_bi_ready/pontes
  04_bi_ready/dicionario_dados
src/
  extraction/
  transformation/
  bi/
  shared/
```

## Como executar

### 1) Instale dependências
```bash
pip install -r requirements.txt
```

### 2) Configure a chave da API
Crie um arquivo `.env` na raiz do projeto:

```env
GEMINI_API_KEY=sua_chave_aqui
MODEL_FLASH=gemini-2.5-flash
MODEL_PRO=gemini-2.5-pro
```

### 3) Coloque os PDFs em:
```text
data/01_raw/pdfs
```

### 4) Execute tudo
```bash
python main.py --stage all
```

### 5) Ou execute por etapa
```bash
python main.py --stage extraction
python main.py --stage transformation
python main.py --stage bi
```

## Saídas principais

- **Extração:** `data/02_extracted/json_raw`
- **Transformação:** `data/03_transformed`
- **BI:** `data/04_bi_ready`

## Observações
- O projeto usa **IDs estáveis**, não UUID aleatório por execução.
- A extração salva **JSON bruto + metadados**.
- A transformação preserva **valor original e valor normalizado** nos campos principais.
- A camada de BI exporta dimensões, fato e pontes.
