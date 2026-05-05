from __future__ import annotations

from typing import Any

from src.normalization_ai.apply_dictionaries import apply_ai_dictionaries
from src.normalization_ai.dictionary_builder import build_ai_dictionaries
from src.shared.config import Settings


def run_ai_normalization(
    settings: Settings,
    logger: Any,
    *,
    only_new_values: bool = False,
    targets: list[str] | None = None,
) -> dict[str, Any]:
    return build_ai_dictionaries(
        settings=settings,
        logger=logger,
        targets=targets,
        only_new_values=only_new_values,
    )


def run_apply_ai_normalization(settings: Settings, logger: Any) -> dict[str, Any]:
    return apply_ai_dictionaries(settings=settings, logger=logger)
