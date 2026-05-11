import pytest

from src.extraction.schema_validator import parse_model_json
from src.shared.schemas import normalize_payload


def test_parse_model_json_accepts_plain_json():
    assert parse_model_json('{"nome_documento": "Teste"}') == {"nome_documento": "Teste"}


def test_parse_model_json_extracts_json_from_surrounding_text():
    assert parse_model_json('texto antes {"ok": true} texto depois') == {"ok": True}


def test_parse_model_json_removes_trailing_commas():
    assert parse_model_json('{"items": ["a",],}') == {"items": ["a"]}


def test_parse_model_json_rejects_text_without_json():
    with pytest.raises(ValueError):
        parse_model_json("sem json aqui")


def test_normalize_payload_accepts_portuguese_false_value():
    payload = normalize_payload({"aplicou_estudo_futuro": "não"})

    assert payload["aplicou_estudo_futuro"] is False
