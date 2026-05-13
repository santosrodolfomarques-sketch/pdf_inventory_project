import pandas as pd
import os
import glob

base_dir = r'c:\pdf_inventory_reestruturado_v6_final_cache_modelos\data\04_bi_ready'
folders = ['dimensoes', 'fatos', 'pontes']

report = '# Resumo de Valores Únicos - Tabelas BI Ready\n\n'

for folder in folders:
    folder_path = os.path.join(base_dir, folder)
    if not os.path.exists(folder_path): continue
    
    report += f'## {folder.capitalize()}\n\n'
    csv_files = glob.glob(os.path.join(folder_path, '*.csv'))
    
    for file in csv_files:
        try:
            df = pd.read_csv(file)
        except Exception as e:
            report += f'### {os.path.basename(file)}\nError reading file: {e}\n\n'
            continue
            
        file_name = os.path.basename(file)
        report += f'### {file_name}\n\n'
        report += f'- **Total de Linhas:** {len(df)}\n'
        report += f'- **Colunas:** {len(df.columns)}\n\n'
        report += '| Coluna | Valores Únicos | Nulos | Exemplo de Valores |\n'
        report += '|---|---|---|---|\n'
        
        for col in df.columns:
            n_unique = df[col].nunique(dropna=False)
            n_nulls = df[col].isnull().sum()
            
            sample_vals = df[col].dropna().unique()
            sample_str = ', '.join([str(x).replace('|', '-') for x in sample_vals[:3]])
            if len(sample_vals) > 3:
                sample_str += ', ...'
                
            report += f'| {col} | {n_unique} | {n_nulls} | {sample_str} |\n'
        
        report += '\n'

with open(r'c:\pdf_inventory_reestruturado_v6_final_cache_modelos\bi_ready_summary.md', 'w', encoding='utf-8') as f:
    f.write(report)
