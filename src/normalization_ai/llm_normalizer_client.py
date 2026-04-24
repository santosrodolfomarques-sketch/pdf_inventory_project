from __future__ import annotations

import json
import time
from typing import Any

from google import genai
from google.genai import types

from src.extraction.schema_validator import parse_model_json


class GeminiDictionaryClient:
    """Cliente LLM para gerar dicionários de normalização/categorização."""

    def __init__(
        self,
        api_key: str,
        model_flash: str,
        model_pro: str,
        max_retries: int = 3,
        logger: Any | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada. Configure no arquivo .env.")
        self.client = genai.Client(api_key=api_key)
        self.model_flash = model_flash
        self.model_pro = model_pro
        self.max_retries = max_retries
        self.logger = logger

    def _log(self, message: str) -> None:
        if self.logger:
            self.logger.info(message)

    def generate_dictionary(self, prompt: str) -> dict[str, Any]:
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            model_name = self.model_flash if attempt < self.max_retries - 1 else self.model_pro
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
                payload = parse_model_json(response.text)
                if "items" not in payload or not isinstance(payload["items"], list):
                    raise ValueError("Resposta sem chave 'items' em formato de lista.")
                return payload
            except Exception as exc:
                last_error = exc
                self._log(
                    f"Erro ao gerar dicionário com {model_name} | tentativa {attempt + 1}/{self.max_retries}: {exc}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)

        raise RuntimeError(f"Falha definitiva ao gerar dicionário: {last_error}")
