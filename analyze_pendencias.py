import pandas as pd
from pathlib import Path

def get_top_pendencies(file_name, col_name, top_n=20):
    path = Path(f"data/04_review/revisoes_aplicadas/{file_name}")
    if not path.exists():
        print(f"File not found: {path}")
        return None
        
    df = pd.read_csv(path, encoding='utf-8-sig')
    
    # Check if the dataframe is empty
    if df.empty:
        print(f"\n--- {file_name} ---")
        print("0 pendencias encontradas. Cobertura total!")
        return None
        
    print(f"\n--- {file_name} (Total pendencias: {len(df)}) ---")
    
    # if 'qtd_ocorrencias' exists, sort by it, otherwise just print top values
    if 'qtd_ocorrencias' in df.columns:
        df = df.sort_values(by='qtd_ocorrencias', ascending=False)
        top = df.head(top_n)
        for _, row in top.iterrows():
            print(f"- {row['valor_normalizado']} (Freq: {row['qtd_ocorrencias']})")
    else:
        # just value counts if no occurrences
        vc = df['valor_normalizado'].value_counts().head(top_n)
        for val, count in vc.items():
            print(f"- {val} (Freq: {count})")

print("ANÁLISE DE MAIORES PENDÊNCIAS PARA AUMENTAR COBERTURA\n")
get_top_pendencies("pendencias_temas.csv", "macrotema")
get_top_pendencies("pendencias_instituicoes.csv", "tipo_instituicao")
get_top_pendencies("pendencias_metodos.csv", "familia_metodo")
get_top_pendencies("pendencias_condicionantes.csv", "macrocondicionante")
