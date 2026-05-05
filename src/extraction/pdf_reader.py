from __future__ import annotations

from pathlib import Path
from typing import Any
import fitz

def extract_text_pdf(
    pdf_path: Path,
    max_pages_begin: int = 30,
    max_pages_end: int = 10,
) -> tuple[str, dict[str, Any]]:
    text_parts: list[str] = []
    metadata: dict[str, Any] = {
        "pages_total": 0,
        "pages_read": [],
        "strategy": f"first_{max_pages_begin}_last_{max_pages_end}",
    }

    try:
        document = fitz.open(pdf_path)
        total_pages = len(document)
        metadata["pages_total"] = total_pages

        pages_to_read = set(range(min(max_pages_begin, total_pages)))
        pages_to_read.update(range(max(0, total_pages - max_pages_end), total_pages))

        for page_number in sorted(pages_to_read):
            page = document.load_page(page_number)
            page_text = page.get_text("text")
            text_parts.append(f"\\n--- Página {page_number + 1} ---\\n{page_text}")
            metadata["pages_read"].append(page_number + 1)

        document.close()
        return "\\n".join(text_parts).strip(), metadata

    except fitz.FileDataError:
        metadata["error"] = "arquivo_corrompido_ou_invalido"
        return "", metadata
    except Exception as exc:
        if "password" in str(exc).lower():
            metadata["error"] = "arquivo_protegido_por_senha"
        else:
            metadata["error"] = f"erro_inesperado: {exc}"
        return "", metadata
