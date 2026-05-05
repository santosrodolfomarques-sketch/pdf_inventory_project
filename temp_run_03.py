def display(*args):
    for a in args: print(a)


import pandas as pd
from pathlib import Path

def get_project_root():
    path = Path.cwd()
    while path != path.parent:
        if (path / "data").exists():
            return path
        path = path.parent
    raise Exception("Raiz do projeto não encontrada")

ROOT = get_project_root()
DIR_REVIEW = ROOT / "data" / "04_review"
DIR_DICIONARIOS = DIR_REVIEW / "dicionarios_manuais"
DIR_SAIDA = DIR_REVIEW / "revisoes_aplicadas"
DIR_LOGS = DIR_REVIEW / "logs_revisao"

for p in [DIR_DICIONARIOS, DIR_SAIDA, DIR_LOGS]: p.mkdir(parents=True, exist_ok=True)

ARQ_ENTRADA = ROOT / "data" / "03_transformed" / "valores_unicos_para_normalizacao" / "valores_unicos_instituicao_responsavel.csv"
ARQ_DICIONARIO = DIR_DICIONARIOS / "dicionario_instituicoes.csv"
ARQ_DIM_CURADA = DIR_SAIDA / "dim_instituicao_curada.csv"
ARQ_PENDENCIAS = DIR_SAIDA / "pendencias_instituicoes.csv"

df = pd.read_csv(ARQ_ENTRADA, encoding='utf-8')
print(f"Linhas: {len(df)}")

if ARQ_DICIONARIO.exists():
    base_revisao = pd.read_csv(ARQ_DICIONARIO, encoding="utf-8-sig")
else:
    base_revisao = df.copy()
    if 'valor_normalizado' not in base_revisao.columns:
        base_revisao['valor_normalizado'] = base_revisao['valor_original']
    
    # Remove missing/empty
    base_revisao['valor_normalizado'] = base_revisao['valor_normalizado'].fillna('').astype(str).str.strip()
    base_revisao = base_revisao[base_revisao['valor_normalizado'] != '']
    
    base_revisao = base_revisao.drop_duplicates('valor_normalizado').copy()
    
    base_revisao['tipo_instituicao'] = ""
    base_revisao['manter'] = True
    base_revisao['observacao'] = ""
    
    if 'qtd_ocorrencias' not in base_revisao.columns:
        base_revisao['qtd_ocorrencias'] = 1
    
    base_revisao = base_revisao[['valor_normalizado', 'tipo_instituicao', 'manter', 'observacao', 'qtd_ocorrencias']]

print(base_revisao.head())

regras = [
    {
        "padrao": r"Ministério|Presidência|Agência Nacional|Secretaria Especial|Receita Federal|IBGE|IPEA|MEC|Ministro|Governo Federal",
        "tipo_instituicao": "Governo Federal",
    },
    {
        "padrao": r"Secretaria de Estado|Governo do Estado|Assembleia Legislativa|Governo Estadual",
        "tipo_instituicao": "Governo Estadual / Distrital",
    },
    {
        "padrao": r"Prefeitura|Câmara Municipal|Governo Municipal",
        "tipo_instituicao": "Governo Municipal",
    },
    {
        "padrao": r"Universidade|Instituto Federal|UF|PUC|FAPESP|CNPq|CAPES|USP|UnB|Academia|Pesquisa",
        "tipo_instituicao": "Academia e Pesquisa",
    },
    {
        "padrao": r"ONG|Instituto|Associação|Fundação|Sociedade Civil|OSCIP|Cooperativa",
        "tipo_instituicao": "Terceiro Setor e Sociedade Civil",
    },
    {
        "padrao": r"Banco|S/A|Ltda|Empresa|Indústria|Comércio|Setor Privado",
        "tipo_instituicao": "Setor Privado",
    },
    {
        "padrao": r"ONU|Banco Mundial|BID|OCDE|CEPAL|PNUD|UNICEF|UNESCO",
        "tipo_instituicao": "Organismos Internacionais",
    }
]

def aplicar_regras(base, regras):
    base = base.copy()
    for regra in regras:
        pendente = base["tipo_instituicao"].isna() | (base["tipo_instituicao"].astype(str).str.strip() == "")
        filtro = base["valor_normalizado"].str.contains(regra["padrao"], case=False, na=False, regex=True) & pendente
        base.loc[filtro, "tipo_instituicao"] = regra["tipo_instituicao"]
    return base

base_revisao = aplicar_regras(base_revisao, regras)
print("Regras aplicadas.")
print(base_revisao.head())

pendencias = base_revisao[base_revisao["tipo_instituicao"].isna() | (base_revisao["tipo_instituicao"].astype(str).str.strip() == "")].copy()

dim_curada = base_revisao[['valor_normalizado', 'tipo_instituicao', 'manter', 'observacao']].copy()

base_revisao.to_csv(ARQ_DICIONARIO, index=False, encoding="utf-8-sig")
dim_curada.to_csv(ARQ_DIM_CURADA, index=False, encoding="utf-8-sig")
pendencias.to_csv(ARQ_PENDENCIAS, index=False, encoding="utf-8-sig")

print(f"Total: {len(base_revisao)}, Pendências: {len(pendencias)}")