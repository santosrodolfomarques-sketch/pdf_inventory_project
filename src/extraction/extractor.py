from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from google import genai
from google.genai import types

from src.core.schemas import ExtractionModel


def extract_pdf_text_and_check(
    pdf_path: Path,
    max_pages_begin: int = 30,
    max_pages_end: int = 10,
) -> tuple[str, dict[str, Any]]:
    """
    Lê o PDF de forma resiliente e checa se o documento contém texto válido
    ou se parece ser um documento puramente escaneado que precisaria de OCR.
    """
    text_parts: list[str] = []
    metadata: dict[str, Any] = {
        "pages_total": 0,
        "pages_read": [],
        "strategy": f"first_{max_pages_begin}_last_{max_pages_end}",
        "needs_ocr": False,
        "error": None,
    }

    try:
        document = fitz.open(pdf_path)
        total_pages = len(document)
        metadata["pages_total"] = total_pages

        # Mapeia as páginas a serem lidas (início e fim)
        pages_to_read = set(range(min(max_pages_begin, total_pages)))
        pages_to_read.update(range(max(0, total_pages - max_pages_end), total_pages))

        total_extracted_chars = 0
        for page_number in sorted(pages_to_read):
            page = document.load_page(page_number)
            page_text = page.get_text("text")
            total_extracted_chars += len(page_text.strip())
            text_parts.append(f"\n--- Página {page_number + 1} ---\n{page_text}")
            metadata["pages_read"].append(page_number + 1)

        document.close()

        extracted_text = "\n".join(text_parts).strip()

        # Detecção de OCR: se há páginas mas nenhum caracter foi extraído
        if total_pages > 0 and total_extracted_chars < 50:
            metadata["needs_ocr"] = True

        return extracted_text, metadata

    except fitz.FileDataError:
        metadata["error"] = "arquivo_corrompido_ou_invalido"
        return "", metadata
    except Exception as exc:
        if "password" in str(exc).lower():
            metadata["error"] = "arquivo_protegido_por_senha"
        else:
            metadata["error"] = f"erro_inesperado: {exc}"
        return "", metadata


class GeminiExtractorClient:
    """Cliente Gemini modernizado para extrair metadados e gerar embeddings sem regex."""

    def __init__(
        self,
        api_key: str,
        model_lite: str = "gemini-2.5-flash-lite",
        model_flash: str = "gemini-2.5-flash",
        model_pro: str = "gemini-2.5-pro",
        max_retries: int = 3,
        logger: Any | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY não configurada. Verifique seu arquivo .env.")
        self.client = genai.Client(api_key=api_key)
        self.model_lite = model_lite
        self.model_flash = model_flash
        self.model_pro = model_pro
        self.max_retries = max_retries
        self.logger = logger

    def _log(self, message: str) -> None:
        if self.logger:
            self.logger.info(message)

    def generate_metadata(self, text_chunk: str) -> tuple[ExtractionModel, str]:
        """
        Gera os metadados do documento utilizando a funcionalidade de
        Structured Outputs nativa do Gemini com o esquema Pydantic,
        percorrendo uma cadeia de fallback de menor custo ao maior custo.
        """
        prompt = f"""
Você é um analista especialista em curadoria e catalogação de documentos técnicos e estudos de futuro.
Sua missão é extrair rigorosamente os metadados do bloco de texto a seguir.

PRINCÍPIOS DE EXTRAÇÃO:
1. Baseie-se apenas em fatos explícitos do texto. Não invente.
2. Identifique e normalize anos para o formato YYYY.
3. Classifique aplicou_estudo_futuro como True APENAS se houver evidência clara de metodologias prospectivas aplicadas (como elaboração de cenários futuros, projeções robustas de longo prazo, painel Delphi, backcasting ou simulações estruturadas). Menções vagas ou simplesmente ter o ano '2030' no título por si só não bastam.
4. Identifique as instituições autoras e parceiras com precisão.

TEXTO DO DOCUMENTO:
{text_chunk}
        """.strip()

        # Cadeia de fallback progressiva
        model_chain = [self.model_lite, self.model_flash, self.model_pro]
        last_error = None

        for attempt in range(self.max_retries):
            # Seleciona o modelo da cadeia com base na tentativa
            idx = min(attempt, len(model_chain) - 1)
            model_name = model_chain[idx]
            
            try:
                if attempt > 0:
                    self._log(f"Fallback acionado: mudando para o modelo {model_name} na tentativa {attempt + 1}")

                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ExtractionModel,
                        temperature=0.1,
                    ),
                )

                parsed_model = ExtractionModel.model_validate_json(response.text)
                return parsed_model, model_name

            except Exception as exc:
                last_error = exc
                wait_seconds = 2 ** attempt
                self._log(f"Falha na tentativa {attempt + 1}/{self.max_retries} ({model_name}): {exc}")
                if attempt < self.max_retries - 1:
                    time.sleep(wait_seconds)

        raise RuntimeError(f"Erro definitivo ao extrair metadados via Gemini: {last_error}")

    def generate_embeddings(self, text: str) -> list[float]:
        """Gera representação vetorial (embeddings) do texto para busca semântica."""
        if not text or len(text.strip()) < 10:
            return []
        try:
            # Limita o texto para caber no limite de tokens do embedding
            truncated_text = text[:30000]
            response = self.client.models.embed_content(
                model="gemini-embedding-2",
                contents=truncated_text,
            )
            if response.embeddings and len(response.embeddings) > 0:
                return response.embeddings[0].values
            return []
        except Exception as exc:
            self._log(f"Falha ao gerar embeddings: {exc}")
            return []
