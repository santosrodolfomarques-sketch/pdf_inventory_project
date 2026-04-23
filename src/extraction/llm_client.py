from __future__ import annotations

import time
from typing import Any

from google import genai
from google.genai import types

from src.extraction.schema_validator import parse_model_json


class GeminiLLMClient:
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

        self.api_key = api_key
        self.model_flash = model_flash
        self.model_pro = model_pro
        self.max_retries = max_retries
        self.logger = logger
        self.client = genai.Client(api_key=self.api_key)

    def _log(self, message: str) -> None:
        if self.logger:
            self.logger.info(message)

    def generate_json(self, prompt: str) -> tuple[dict[str, Any], str]:
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            model_name = self.model_flash if attempt < self.max_retries - 1 else self.model_pro

            try:
                if attempt == self.max_retries - 1 and self.max_retries > 1:
                    self._log("Fallback para modelo PRO devido a falhas anteriores.")

                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )

                payload = parse_model_json(response.text)
                return payload, model_name

            except Exception as exc:
                last_error = exc
                wait_seconds = 2 ** attempt
                self._log(
                    f"Erro na chamada ao Gemini ({model_name}) | "
                    f"tentativa {attempt + 1}/{self.max_retries}: {exc}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(wait_seconds)

        raise RuntimeError(f"Falha definitiva na chamada ao Gemini: {last_error}")