from src.bi.semantic_helpers import (
    classify_condition_category,
    classify_institution_type,
    classify_macrotema,
    classify_method_family,
    classify_method_nature,
    classify_subtema,
)


def test_theme_rules_reduce_common_uncategorized_topics():
    assert classify_macrotema("Segurança Alimentar") == "Desenvolvimento Social"
    assert classify_subtema("Poluição do Ar") == "Clima"
    assert classify_subtema("Recursos Energéticos") == "Energia"


def test_method_rules_classify_participatory_methods():
    family = classify_method_family("Oficinas Técnicas")

    assert family == "Painel de Especialistas (Delphi/Workshops)"
    assert classify_method_nature(family, "Oficinas Técnicas") == "Qualitativo"


def test_local_enrichment_rules_classify_institutions_and_conditions():
    assert classify_institution_type("Ministério do Meio Ambiente") == "Governo"
    assert classify_institution_type("Universidade Federal de Lavras") == "Universidade"
    assert classify_condition_category("Aumento do desmatamento") == "Ambiental"
