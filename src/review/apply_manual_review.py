import pandas as pd
from pathlib import Path


def apply_tema_review(base_dir: Path):
    print("Aplicando revisão manual de temas...")

    # Caminhos
    path_temas = base_dir / "data/03_transformed/tabelas_normalizadas/temas_normalizados.csv"
    path_dict = base_dir / "data/04_review/dicionarios_manuais/dicionario_temas.csv"
    path_saida = base_dir / "data/04_review/revisoes_aplicadas/temas_enriquecidos.csv"

    temas = pd.read_csv(path_temas)
    dicionario = pd.read_csv(path_dict)

    # Merge
    df = temas.merge(
        dicionario,
        on="tema_normalizado",
        how="left"
    )

    # Validação
    faltantes = df["macrotema"].isna().sum()

    print(f"Temas sem classificação: {faltantes}")

    # Salvar
    path_saida.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path_saida, index=False, encoding="utf-8-sig")

    print("Arquivo salvo em:", path_saida)

    return df