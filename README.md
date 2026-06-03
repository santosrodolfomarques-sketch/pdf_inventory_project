# PDF Inventory Project - Reestruturação Enterprise & Curadoria Assistida por IA

Pipeline de dados modular de ponta a ponta projetado para inventariar PDFs técnicos, executar extração de metadados, realizar normalização taxonômica assistida por Machine Learning Ativo e estruturar dados prontos para Business Intelligence (BI/Power BI).

---

## 🏛️ Arquitetura e Camadas do Sistema

O projeto é estruturado em camadas desacopladas que se comunicam através de arquivos estruturados e caches locais persistentes:

1. **Ingestão Incremental Multimodal (Gemini Files API & Ciclo Seguro)**  
   Os PDFs em `data/01_raw/pdfs` são carregados de forma temporária para a **Files API** do Gemini. O modelo `gemini-3.5-flash` lê nativamente o documento (texto e estrutura visual). Imediatamente após a conclusão, o arquivo físico é **excluído de forma explícita e definitiva** dos servidores da Google via `client.files.delete` em blocos `finally` de tratamento, garantindo total privacidade dos dados.
   * *Fallback automático:* Se o processamento falhar, o pipeline faz o fallback para o `gemini-2.5-pro` antes de desistir.

2. **Detecção de Duplicados Semânticos**  
   Os textos representativos dos PDFs são submetidos à API de embeddings (`gemini-embedding-2`) para gerar vetores de representação semântica do documento. Ao carregar um novo arquivo, o sistema calcula a similaridade de cosseno contra os PDFs já homologados:
   * **Se similaridade $\ge 85\%$:** O sistema aciona um alerta visual e direciona o usuário para o fluxo de resolução de conflitos.

3. **Resolução Visual de Conflitos e Reprocessamento (Streamlit)**  
   * **Mesclagem de Metadados:** Se um duplicado é detectado e o usuário deseja mesclar, uma grade interativa exibe as diferenças lado a lado (Dados da Base vs. Dados do Novo PDF) para cada campo, permitindo escolher campo a campo quais dados manter.
   * **Reprocessamento:** Na ficha do documento, curadores podem disparar o reprocessamento via IA de qualquer PDF original, revisando os novos metadados sugeridos em um formulário antes de salvá-los.

4. **Normalização por Aprendizado Ativo (Active Learning ML & LLM)**  
   Lê os valores brutos extraídos (setores, temas, métodos, etc.) e mapeia sob termos normalizados de forma híbrida:
   * **ML Exato e Ortográfico:** Limpa acentuações e resolve pequenos erros de digitação (SequenceMatcher).
   * **Similaridade Semântica (Embeddings):** Compara cosseno contra mapeamentos já aprovados pelo curador em execuções passadas.
   * **Otimização de Lote (Batching & RPM Safety):** Os termos de consulta novos são enviados em lotes de 100 termos com timeouts de 20s, retentativas automáticas com backoff exponencial (`2s`, `4s`) e pausas de `1.5s` entre lotes, respeitando as taxas de RPM da API da Google.
   * **Fallback de LLM:** Se o ML local não classificar o termo com confiança alta, o `gemini-3.1-flash-lite` classifica o lote.

5. **Taxonomias Científicas de Foresight (ISFF)**  
   O normalizador categoriza e audita os metadados sob rigorosos padrões científicos:
   * **STEEPV:** Setores, Temas e Condicionantes são categorizados rigidamente nas dimensões *Social*, *Tecnológico*, *Econômico*, *Ecológico/Ambiental*, *Político/Governança*, ou *Valores/Cultura*.
   * **Popper Foresight Diamond:** Métodos são classificados sob as 4 famílias de Rafael Popper (*Criatividade*, *Expertise*, *Interação*, *Evidência*) e sua natureza (*Qualitativo*, *Quantitativo*, *Semi-Quantitativo*).

6. **Exploração Dinâmica e Explosão de Listas (BI Ready)**  
   Na aba "Cruzar & Explorar", múltiplos valores separados por vírgula em listas (ex: setores, temas, métodos) são explodidos automaticamente para contagem analítica. Gráficos dinâmicos de barras empilhadas (stacked) ou agrupadas (grouped) ilustram as correlações por categorias.
   * **Power BI Star Schema:** O botão lateral exporta fatos, dimensões e pontes higienizadas para o diretório `data/04_bi_ready`.

7. **Logs em Tempo Real (Estilo PowerShell)**  
   Integração do `StreamlitLogHandler` na interface do Streamlit. Curadores visualizam exatamente qual lote, termo ou arquivo está sendo lido/normalizado em tempo real.

---

## 🚀 Instalação e Configuração

### 1. Instalação do ambiente com `uv`

```powershell
uv venv --seed
.venv\Scripts\Activate.ps1
uv pip install --link-mode=copy -r requirements.txt
```

### 2. Configuração de Variáveis de Ambiente

Crie o arquivo `.env` a partir do template:

```powershell
copy .env.example .env
```

Abra o `.env` e configure sua chave de API e os novos modelos:

```ini
GEMINI_API_KEY=sua_chave_de_api_aqui
MODEL_LITE=gemini-3.1-flash-lite
MODEL_FLASH=gemini-3.5-flash
MODEL_PRO=gemini-2.5-pro
MAX_RETRIES=3
MAX_PAGES_BEGIN=15
MAX_PAGES_END=0
```

---

## 🛠️ Execução do Sistema

### 1. Iniciar a Interface Gráfica (Streamlit Curation Hub)

```powershell
.venv\Scripts\streamlit run src/app.py
```

### 2. Execução via CLI (Modo Pipeline)

Se preferir rodar etapas individuais no terminal:

```powershell
# Executar a ingestão e extração de novos PDFs físicos
python main.py --stage extraction

# Consolidar os caches JSON brutos
python main.py --stage transformation

# Executar a normalização (ML Ativo + LLM) dos termos únicos
python main.py --stage ai-normalization --only-new-values

# Aplicar os dicionários aprovados nas tabelas de dados
python main.py --stage apply-normalization

# Gerar e exportar o Star Schema pronto para o Power BI
python main.py --stage bi
```

---

## 🧪 Validação e Testes Automatizados

A suíte de testes unitários cobre validações de esquemas, similaridade matemática de cosseno, leitura de caches locais, normalizadores ortográficos e correspondência de taxonomias (STEEPV/Popper Foresight Diamond).

Execute todos os testes com:

```powershell
.venv\Scripts\pytest
```

---

## 📂 Diretórios do Projeto

* `data/01_raw/pdfs/`: Pasta física contendo os PDFs originais.
* `data/02_extracted/json_raw/`: Cache local persistente das extrações brutas de cada PDF (formato `nome__hash.json`).
* `data/03_transformed/tabelas_base/`: Bases consolidadas unificadas a partir dos caches locais.
* `data/03_transformed/normalizacao_ia/dicionarios_normalizacao/`: Tabelas CSV com os termos normalizados e categorizados auditáveis.
* `data/04_bi_ready/`: Tabelas Star Schema prontas para conexão com Power BI.
* `src/extraction/`: Ingestão, upload e cálculo de embeddings/duplicados semânticos.
* `src/normalization/`: Normalização léxica híbrida por ML ativo e LLM (Gemini 3.1).
* `tests/`: Suíte de testes automatizados (`pytest`).
