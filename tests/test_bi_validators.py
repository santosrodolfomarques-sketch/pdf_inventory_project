import pandas as pd

from src.bi.validators import run_bi_validations


def test_bi_validation_flags_fact_row_count_mismatch():
    dimensions = {
        "dim_documento": pd.DataFrame({"sk_documento": [1, 2]}),
    }
    fact = pd.DataFrame({
        "sk_fato_inventario": [1],
        "sk_documento": [1],
        "sk_tempo": [1],
        "sk_setor": [1],
        "sk_abrangencia": [1],
        "sk_metodologia": [1],
        "sk_qualidade": [1],
    })
    source = pd.DataFrame({"id_documento_logico": ["a", "b"]})

    report = run_bi_validations(dimensions, fact, source=source)

    assert report["status"] == "error"
    assert report["checks"][0]["teste"] == "quantidade_linhas_compativel_com_base"


def test_bi_validation_accepts_matching_fact_row_count():
    dimensions = {
        "dim_documento": pd.DataFrame({"sk_documento": [1]}),
    }
    fact = pd.DataFrame({
        "sk_fato_inventario": [1],
        "sk_documento": [1],
        "sk_tempo": [1],
        "sk_setor": [1],
        "sk_abrangencia": [1],
        "sk_metodologia": [1],
        "sk_qualidade": [1],
    })
    source = pd.DataFrame({"id_documento_logico": ["a"]})

    report = run_bi_validations(dimensions, fact, source=source)

    assert report["checks"][0]["status"] == "ok"
