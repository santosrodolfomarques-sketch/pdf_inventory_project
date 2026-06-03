from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
DATA_DIR = PROJECT_ROOT / "data"

# Caminhos do Pipeline
RAW_PDF_DIR = DATA_DIR / "01_raw" / "pdfs"
EXTRACTED_DIR = DATA_DIR / "02_extracted"
EXTRACTED_JSON_DIR = EXTRACTED_DIR / "json_raw"
EXTRACTION_LOG_DIR = EXTRACTED_DIR / "logs"
EXTRACTION_CONTROL_DIR = EXTRACTED_DIR / "controle_processamento"

TRANSFORMED_DIR = DATA_DIR / "03_transformed"
TRANSFORMED_BASE_DIR = TRANSFORMED_DIR / "tabelas_base"
TRANSFORMED_NORMALIZED_DIR = TRANSFORMED_DIR / "tabelas_normalizadas"
TRANSFORMED_PENDING_DIR = TRANSFORMED_DIR / "pendencias"
TRANSFORMED_UNIQUE_DIR = TRANSFORMED_DIR / "valores_unicos_para_normalizacao"

AI_NORMALIZATION_DIR = TRANSFORMED_DIR / "normalizacao_ia"
AI_DICTIONARY_DIR = AI_NORMALIZATION_DIR / "dicionarios_normalizacao"
AI_DICTIONARY_REVIEW_DIR = AI_NORMALIZATION_DIR / "revisao_manual"
AI_APPLIED_DIR = AI_NORMALIZATION_DIR / "bases_normalizadas"

ENRICHMENT_DIR = TRANSFORMED_DIR / "enrichment_ai"

BI_READY_DIR = DATA_DIR / "04_bi_ready"
BI_DIM_DIR = BI_READY_DIR / "dimensoes"
BI_FACT_DIR = BI_READY_DIR / "fatos"
BI_BRIDGE_DIR = BI_READY_DIR / "pontes"
BI_DICT_DIR = BI_READY_DIR / "dicionario_dados"

# Mapeamentos default e taxonomias legado
DEFAULT_TAXONOMIA_METODOS = [
    "Extrapolação de Tendências",
    "Cenários Prospectivos",
    "Painel de Especialistas (Delphi/Workshops)",
    "Modelagem e Simulação Quantitativa",
    "Visão de Futuro / Backcasting",
    "Análise de Impacto Cruzado",
    "Outros",
]

DEFAULT_DOCUMENT_TYPES = {
    "plano": "Plano", "plan": "Plano",
    "estrategia": "Estratégia", "strategy": "Estratégia",
    "relatorio": "Relatório", "report": "Relatório",
    "estudo": "Estudo", "diagnostico": "Diagnóstico",
    "diagnóstico": "Diagnóstico", "agenda": "Agenda",
    "guia": "Guia", "livro": "Livro", "policy brief": "Policy Brief"
}

DEFAULT_TERRITORIAL_SCOPE = {
    "brasil": "Nacional", "brazil": "Nacional", "nacional": "Nacional",
    "regional": "Regional", "global": "Global", "estadual": "Estadual",
    "state": "Estadual", "municipal": "Municipal", "local": "Municipal"
}

DEFAULT_SECTOR_MAP = {
    "sociedade civil": "Sociedade Civil", "terceiro setor": "Terceiro Setor",
    "saude": "Saúde", "saúde": "Saúde", "educacao": "Educação", "educação": "Educação",
    "energia": "Energia", "transporte": "Transporte", "clima": "Clima",
    "economia": "Economia", "seguranca": "Segurança", "segurança": "Segurança",
    "infraestrutura": "Infraestrutura", "meio ambiente": "Meio Ambiente", "agricultura": "Agricultura"
}


@dataclass(slots=True)
class Settings:
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    model_lite: str = field(default_factory=lambda: os.getenv("MODEL_LITE", "gemini-2.5-flash-lite"))
    model_flash: str = field(default_factory=lambda: os.getenv("MODEL_FLASH", "gemini-2.5-flash"))
    model_pro: str = field(default_factory=lambda: os.getenv("MODEL_PRO", "gemini-2.5-pro"))
    max_retries: int = field(default_factory=lambda: int(os.getenv("MAX_RETRIES", "3")))
    max_pages_begin: int = field(default_factory=lambda: int(os.getenv("MAX_PAGES_BEGIN", "30")))
    max_pages_end: int = field(default_factory=lambda: int(os.getenv("MAX_PAGES_END", "10")))
    max_chars_per_chunk: int = field(default_factory=lambda: int(os.getenv("MAX_CHARS_PER_CHUNK", "120000")))
    chunk_overlap: int = field(default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "5000")))
    pause_between_calls: float = field(default_factory=lambda: float(os.getenv("PAUSE_BETWEEN_CALLS", "1.2")))
    ai_dictionary_batch_size: int = field(default_factory=lambda: int(os.getenv("AI_DICTIONARY_BATCH_SIZE", "30")))
    ai_apply_min_confidence: str = field(default_factory=lambda: os.getenv("AI_APPLY_MIN_CONFIDENCE", "alta"))

    # Pesos configuráveis para cálculo do score de qualidade BI
    weight_name: float = field(default_factory=lambda: float(os.getenv("WEIGHT_NAME", "0.15")))
    weight_year: float = field(default_factory=lambda: float(os.getenv("WEIGHT_YEAR", "0.12")))
    weight_horizon: float = field(default_factory=lambda: float(os.getenv("WEIGHT_HORIZON", "0.10")))
    weight_sector: float = field(default_factory=lambda: float(os.getenv("WEIGHT_SECTOR", "0.10")))
    weight_scope: float = field(default_factory=lambda: float(os.getenv("WEIGHT_SCOPE", "0.08")))
    weight_themes: float = field(default_factory=lambda: float(os.getenv("WEIGHT_THEMES", "0.15")))
    weight_refs: float = field(default_factory=lambda: float(os.getenv("WEIGHT_REFS", "0.15")))
    weight_methods: float = field(default_factory=lambda: float(os.getenv("WEIGHT_METHODS", "0.15")))

    taxonomia_metodos: list[str] = field(default_factory=lambda: DEFAULT_TAXONOMIA_METODOS.copy())
    document_type_map: dict[str, str] = field(default_factory=lambda: DEFAULT_DOCUMENT_TYPES.copy())
    territorial_scope_map: dict[str, str] = field(default_factory=lambda: DEFAULT_TERRITORIAL_SCOPE.copy())
    sector_map: dict[str, str] = field(default_factory=lambda: DEFAULT_SECTOR_MAP.copy())

    # Diretorios mapeados dinamicamente
    @property
    def raw_pdf_dir(self) -> Path: return RAW_PDF_DIR
    @property
    def extracted_json_dir(self) -> Path: return EXTRACTED_JSON_DIR
    @property
    def extraction_log_dir(self) -> Path: return EXTRACTION_LOG_DIR
    @property
    def extraction_control_dir(self) -> Path: return EXTRACTION_CONTROL_DIR
    @property
    def transformed_base_dir(self) -> Path: return TRANSFORMED_BASE_DIR
    @property
    def transformed_normalized_dir(self) -> Path: return TRANSFORMED_NORMALIZED_DIR
    @property
    def transformed_pending_dir(self) -> Path: return TRANSFORMED_PENDING_DIR
    @property
    def transformed_unique_dir(self) -> Path: return TRANSFORMED_UNIQUE_DIR
    @property
    def ai_normalization_dir(self) -> Path: return AI_NORMALIZATION_DIR
    @property
    def ai_dictionary_dir(self) -> Path: return AI_DICTIONARY_DIR
    @property
    def ai_dictionary_review_dir(self) -> Path: return AI_DICTIONARY_REVIEW_DIR
    @property
    def ai_applied_dir(self) -> Path: return AI_APPLIED_DIR
    @property
    def enrichment_dir(self) -> Path: return ENRICHMENT_DIR
    @property
    def bi_dim_dir(self) -> Path: return BI_DIM_DIR
    @property
    def bi_fact_dir(self) -> Path: return BI_FACT_DIR
    @property
    def bi_bridge_dir(self) -> Path: return BI_BRIDGE_DIR
    @property
    def bi_dict_dir(self) -> Path: return BI_DICT_DIR


def get_settings() -> Settings:
    return Settings()
