from __future__ import annotations

import argparse
from src.core.config import get_settings
from src.shared.logging_utils import setup_logger
from src.shared.utils import ensure_dirs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline enterprise reestruturado para inventário de PDFs (Caminho B).")
    parser.add_argument(
        "--stage",
        choices=[
            "all",
            "extraction",
            "transformation",
            "ai-normalization",
            "apply-normalization",
            "bi",
        ],
        default="all",
        help="Etapa a executar.",
    )
    parser.add_argument(
        "--force-reprocess",
        action="store_true",
        help="Ignora o cache da camada de extração e força consulta ao Gemini.",
    )
    parser.add_argument(
        "--only-new-values",
        action="store_true",
        help="Na normalização por IA, envia apenas valores que ainda não existem nos dicionários.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()

    # Assegura que todas as pastas físicas do pipeline existam
    ensure_dirs([
        settings.raw_pdf_dir,
        settings.extracted_json_dir,
        settings.extraction_log_dir,
        settings.extraction_control_dir,
        settings.transformed_base_dir,
        settings.transformed_normalized_dir,
        settings.transformed_pending_dir,
        settings.transformed_unique_dir,
        settings.ai_normalization_dir,
        settings.ai_dictionary_dir,
        settings.ai_dictionary_review_dir,
        settings.ai_applied_dir,
        settings.enrichment_dir,
        settings.bi_dim_dir,
        settings.bi_fact_dir,
        settings.bi_bridge_dir,
        settings.bi_dict_dir,
    ])

    logger = setup_logger("pdf_inventory", settings.extraction_log_dir / "pipeline.log")
    stage = args.stage

    logger.info(f"Iniciando pipeline PDF Inventory - Etapa: {stage}")

    if stage == "all":
        from src.extraction.pipeline import run_extraction
        from src.transformation.pipeline import run_transformation
        from src.normalization.pipeline import run_ai_normalization, apply_ai_dictionaries
        from src.bi.pipeline import run_bi_preparation

        logger.info("--- 1. EXTRATÃO (LLM + Pydantic + Embeddings) ---")
        run_extraction(settings, logger, force_reprocess=args.force_reprocess)

        logger.info("--- 2. TRANSFORMAÇÃO & DEDUPLICAÇÃO ---")
        run_transformation(settings, logger)

        logger.info("--- 3. NORMALIZAÇÃO IA (Batch Dictionaries) ---")
        run_ai_normalization(settings, logger, only_new_values=args.only_new_values)

        logger.info("--- 4. APLICAÇÃO DOS DICIONÁRIOS ---")
        apply_ai_dictionaries(settings, logger)

        logger.info("--- 5. MODELAGEM ESTRELA BI ---")
        run_bi_preparation(settings, logger)

    elif stage == "extraction":
        from src.extraction.pipeline import run_extraction
        run_extraction(settings, logger, force_reprocess=args.force_reprocess)

    elif stage == "transformation":
        from src.transformation.pipeline import run_transformation
        run_transformation(settings, logger)

    elif stage == "ai-normalization":
        from src.normalization.pipeline import run_ai_normalization
        run_ai_normalization(settings, logger, only_new_values=args.only_new_values)

    elif stage == "apply-normalization":
        from src.normalization.pipeline import apply_ai_dictionaries
        apply_ai_dictionaries(settings, logger)

    elif stage == "bi":
        from src.bi.pipeline import run_bi_preparation
        run_bi_preparation(settings, logger)

    logger.info("Execução do pipeline concluída com sucesso.")


if __name__ == "__main__":
    main()