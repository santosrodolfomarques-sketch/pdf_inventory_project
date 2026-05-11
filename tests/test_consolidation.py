from src.transformation.consolidation import consolidate_records


def test_consolidate_records_preserves_source_files():
    records = [
        {
            "id_documento_logico": "doc_1",
            "source_file_name": "001.pdf",
            "temas": ["Clima"],
            "temas_norm": ["Clima"],
        },
        {
            "id_documento_logico": "doc_1",
            "source_file_name": "002.pdf",
            "temas": ["Energia"],
            "temas_norm": ["Energia"],
        },
    ]

    [consolidated] = consolidate_records(records)

    assert consolidated["qtd_arquivos_origem"] == 2
    assert consolidated["source_files"] == ["001.pdf", "002.pdf"]
    assert consolidated["temas"] == ["Clima", "Energia"]
