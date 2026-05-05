from __future__ import annotations

import time
from typing import Any

from google import genai
from google.genai import types

from src.extraction.schema_validator import parse_model_json
from src.shared.llm_timeout import run_with_timeout


class EnrichmentClient:
    def __init__(
        self,
        api_key: str,
        model_simple: str,
        model_context: str,
        max_retries: int = 3,
        timeout_seconds: int = 240,
        context_model_min_chars: int = 90000,
        logger: Any | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada. Configure no arquivo .env.")
        self.client = genai.Client(api_key=api_key)
        self.model_simple = model_simple
        self.model_context = model_context
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.context_model_min_chars = context_model_min_chars
        self.logger = logger

    def _log(self, msg: str) -> None:
        if self.logger:
            self.logger.info(msg)

    def _model_for_attempt(self, prompt: str, attempt: int) -> str:
        if len(prompt) >= self.context_model_min_chars:
            return self.model_context
        return self.model_simple if attempt < self.max_retries - 1 else self.model_context

    def _call_model(self, model_name: str, prompt: str):
        return self.client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

    def _call_model_with_timeout(self, model_name: str, prompt: str):
        self._log(
            f"Iniciando chamada LLM de enrichment | modelo={model_name} | chars_prompt={len(prompt)} | timeout={self.timeout_seconds}s"
        )
        response = run_with_timeout(
            lambda: self._call_model(model_name, prompt),
            timeout_seconds=self.timeout_seconds,
        )
        self._log(f"Resposta LLM de enrichment recebida | modelo={model_name}")
        return response

    def run(self, prompt: str) -> tuple[dict[str, Any], str]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            model_name = self._model_for_attempt(prompt, attempt)
            try:
                if model_name == self.model_context and (attempt > 0 or len(prompt) >= self.context_model_min_chars):
                    self._log(f"Enrichment usando modelo de maior contexto: {model_name}")
                response = self._call_model_with_timeout(model_name, prompt)
                payload = parse_model_json(response.text)
                if "items" not in payload or not isinstance(payload["items"], list):
                    raise ValueError("Resposta sem chave 'items' em formato de lista.")
                return payload, model_name
            except Exception as exc:
                last_error = exc
                wait_seconds = min(2 ** attempt, 30)
                self._log(f"Erro no enrichment com {model_name} | tentativa {attempt + 1}/{self.max_retries}: {exc}")
                if attempt < self.max_retries - 1:
                    self._log(f"Aguardando {wait_seconds}s antes da próxima tentativa de enrichment.")
                    time.sleep(wait_seconds)
        raise RuntimeError(f"Falha definitiva no enrichment: {last_error}")
