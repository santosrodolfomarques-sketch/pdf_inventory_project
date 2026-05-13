import pandas as pd
import os
import glob
import re

dir_path = r"c:\pdf_inventory_reestruturado_v6_final_cache_modelos\data\04_bi_ready\dimensoes"
csv_files = glob.glob(os.path.join(dir_path, "*.csv"))

# termos para buscar (exact match ou substring, usando re para pegar palavras isoladas seria melhor, mas `in` já resolve para substrings como "não informado")
termos = ["outro", "não classificado", "nao classificado", "não informado", "nao informado", "não especificado", "nao especificado", "nd", "n/a", "não categorizado", "nao categorizado", "sem classificacao", "sem classificação", "nenhum", "desconhecido"]

def is_similar(val):
    if pd.isna(val):
        return False
    val_str = str(val).lower().strip()
    return any(termo in val_str for termo in termos)

results = []

for file in csv_files:
    try:
        df = pd.read_csv(file, sep=',')
    except Exception as e:
        try:
            df = pd.read_csv(file, sep=';')
        except Exception as e2:
            print(f"Error reading {file}: {e2}")
            continue
        
    table_name = os.path.basename(file)
    
    for col in df.columns:
        total_rows = len(df)
        if total_rows == 0:
            continue
            
        count_similar = df[col].apply(is_similar).sum()
        pct = (count_similar / total_rows) * 100
        
        if pct > 0:
            results.append({
                "Tabela": table_name,
                "Coluna": col,
                "Quantidade": count_similar,
                "Total": total_rows,
                "Percentual (%)": round(pct, 2)
            })

results_df = pd.DataFrame(results)
if not results_df.empty:
    results_df = results_df.sort_values(by=["Tabela", "Percentual (%)"], ascending=[True, False])
    print(results_df.to_string(index=False))
else:
    print("Nenhum dado encontrado.")
