def apply_enrichment(df, settings):

    inst_dict = pd.read_csv(settings.enrichment_dir / "dicionario_instituicoes_enriquecido.csv")

    df = df.merge(
        inst_dict,
        left_on="instituicao_responsavel_norm",
        right_on="valor_original",
        how="left"
    )

    return df