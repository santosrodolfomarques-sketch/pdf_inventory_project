from __future__ import annotations

import argparse

from src.bi.bi_pipeline import run_bi_preparation
from src.extraction.extraction_pipeline import run_extraction
from src.shared.config import (
    BI_BRIDGE_DIR,
    BI_DICT_DIR,
    BI_DIM_DIR,
    BI_FACT_DIR,
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
from src.transformation.transformation_pipeline import run_transformation

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline reestruturado para inventário de PDFs.")
    parser.add_argument(
        "--stage",
        choices=["all", "extraction", "transform", "transformation", "bi"],
        default="all",
        help="Etapa a executar.",
    )
    parser.add_argument(
        "--force-reprocess",
        action="store_true",
        help="Ignora cache da camada de extração.",
    )
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
        BI_DIM_DIR,
        BI_FACT_DIR,
        BI_BRIDGE_DIR,
        BI_DICT_DIR,
    ])

    logger = setup_logger("pdf_inventory", EXTRACTION_LOG_DIR / "pipeline.log")

    stage = args.stage
    if stage == "all":
        run_extraction(settings, logger, force_reprocess=args.force_reprocess)
        run_transformation(settings, logger)
        run_bi_preparation(settings, logger)
    elif stage == "extraction":
        run_extraction(settings, logger, force_reprocess=args.force_reprocess)
    elif stage in {"transform", "transformation"}:
        run_transformation(settings, logger)
    elif stage == "bi":
        run_bi_preparation(settings, logger)

if __name__ == "__main__":
    main()
