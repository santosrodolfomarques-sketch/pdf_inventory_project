import pandas as pd
import os
import glob
import json

base_dir = r'c:\pdf_inventory_reestruturado_v6_final_cache_modelos\data\04_bi_ready\dimensoes'
csv_files = glob.glob(os.path.join(base_dir, '*.csv'))

results = []

for file in csv_files:
    df = pd.read_csv(file, encoding='utf-8')
    file_name = os.path.basename(file)
    total_rows = len(df)
    
    file_info = {'file': file_name, 'columns': []}
    
    for col in df.columns:
        if df[col].dtype == object:
            series = df[col].astype(str).str.lower().str.strip()
            # replace unicode chars to avoid regex match issues if needed, or just match exactly
            count = series.isin([
                'não classificado', 'não classificada', 'nao classificado', 
                'não informado', 'nao informado', 'outros / revisar', 'revisar manualmente'
            ]).sum()
            
            if count > 0:
                pct = (count / total_rows) * 100
                file_info['columns'].append({'column': col, 'unclassified': int(count), 'total': int(total_rows), 'pct': pct})
    
    if file_info['columns']:
        results.append(file_info)

with open(r'c:\pdf_inventory_reestruturado_v6_final_cache_modelos\pct_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
