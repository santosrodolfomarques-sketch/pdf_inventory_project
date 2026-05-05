from __future__ import annotations

import argparse

from src.shared.config import (
    AI_APPLIED_DIR,
    AI_BATCH_CACHE_DIR,
    AI_CONTROL_DIR,
    AI_DICTIONARY_DIR,
    AI_DICTIONARY_REVIEW_DIR,
    AI_NORMALIZATION_DIR,
    BI_BRIDGE_DIR,
    BI_DICT_DIR,
    BI_DIM_DIR,
    BI_FACT_DIR,
    ENRICHMENT_DIR,
    EXTRACTED_JSON_DIR,
    EXTRACTION_CONTROL_DIR,
    EXTRACTION_LOG_DIR,
    RAW_PDF_DIR,
    TRANSFORMED_BASE_DIR,
    TRANSFORMED_NORMALIZED_DIR,
    TRANSFORMED_PENDING_DIR,
    TRANSFORMED_UNIQUE_DIR,
    get_settings,
)
from src.shared.logging_utils import setup_logger
from src.shared.utils import ensure_dirs


def _parse_targets(raw_targets: str | None) -> list[str] | None:
    if not raw_targets:
        return None
    return [item.strip() for item in raw_targets.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline reestruturado para inventário de PDFs.")
    parser.add_argument(
        "--stage",
        choices=[
            "all",
            "extraction",
            "retry-failed",
            "transform",
            "transformation",
            "ai-normalization",
            "apply-normalization",
            "apply-manual-review",
            "enrichment",
            "bi",
        ],
        default="all",
        help="Etapa a executar.",
    )
    parser.add_argument("--force-reprocess", action="store_true", help="Ignora cache da camada de extração.")
    parser.add_argument("--only-new-values", action="store_true", help="Na normalização por IA, envia apenas valores que ainda não existem nos dicionários.")
    parser.add_argument("--targets", default=None, help="Alvos da normalização por IA, separados por vírgula. Ex.: setor,temas,metodos")
    parser.add_argument("--limit", type=int, default=None, help="Limita a quantidade de PDFs processados na extração.")
    parser.add_argument("--offset", type=int, default=0, help="Pula os N primeiros PDFs na extração.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()

    ensure_dirs([
        RAW_PDF_DIR,
        EXTRACTED_JSON_DIR,
        EXTRACTION_LOG_DIR,
        EXTRACTION_CONTROL_DIR,
        TRANSFORMED_BASE_DIR,
        TRANSFORMED_NORMALIZED_DIR,
        TRANSFORMED_PENDING_DIR,
        TRANSFORMED_UNIQUE_DIR,
        AI_NORMALIZATION_DIR,
        AI_DICTIONARY_DIR,
        AI_DICTIONARY_REVIEW_DIR,
        AI_APPLIED_DIR,
        AI_BATCH_CACHE_DIR,
        AI_CONTROL_DIR,
        ENRICHMENT_DIR,
        BI_DIM_DIR,
        BI_FACT_DIR,
        BI_BRIDGE_DIR,
        BI_DICT_DIR,
    ])

    logger = setup_logger("pdf_inventory", EXTRACTION_LOG_DIR / "pipeline.log")
    targets = _parse_targets(args.targets)
    stage = args.stage

    if stage == "all":
        from src.extraction.extraction_pipeline import run_extraction
        from src.transformation.transformation_pipeline import run_transformation
        from src.normalization_ai.normalization_ai_pipeline import run_ai_normalization, run_apply_ai_normalization
        from src.enrichment_ai.enrichment_pipeline import run_enrichment
        from src.bi.bi_pipeline import run_bi_preparation

        run_extraction(settings, logger, force_reprocess=args.force_reprocess, limit=args.limit, offset=args.offset)
        run_transformation(settings, logger)
        run_ai_normalization(settings, logger, only_new_values=args.only_new_values, targets=targets)
        run_apply_ai_normalization(settings, logger)
        run_enrichment(settings, logger)
        run_bi_preparation(settings, logger)

    elif stage == "extraction":
        from src.extraction.extraction_pipeline import run_extraction
        run_extraction(settings, logger, force_reprocess=args.force_reprocess, limit=args.limit, offset=args.offset)

    elif stage == "retry-failed":
        from src.extraction.extraction_pipeline import run_extraction
        run_extraction(settings, logger, force_reprocess=args.force_reprocess, only_failed=True, limit=args.limit, offset=args.offset)

    elif stage in {"transform", "transformation"}:
        from src.transformation.transformation_pipeline import run_transformation
        run_transformation(settings, logger)

    elif stage == "ai-normalization":
        from src.normalization_ai.normalization_ai_pipeline import run_ai_normalization
        run_ai_normalization(settings, logger, only_new_values=args.only_new_values, targets=targets)

    elif stage == "apply-normalization":
        from src.normalization_ai.normalization_ai_pipeline import run_apply_ai_normalization
        run_apply_ai_normalization(settings, logger)

    elif stage == "enrichment":
        from src.enrichment_ai.enrichment_pipeline import run_enrichment
        run_enrichment(settings, logger)

    elif stage == "apply-manual-review":
        from pathlib import Path
        from src.review.apply_manual_review import apply_tema_review

        apply_tema_review(Path.cwd())

    elif stage == "bi":
        from src.bi.bi_pipeline import run_bi_preparation
        run_bi_preparation(settings, logger)
    
    

if __name__ == "__main__":
    main()
