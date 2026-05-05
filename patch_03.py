import json

with open("notebooks/03_revisao_instituicoes.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

for cell in nb["cells"]:
    if cell["cell_type"] == "code":
        source = "".join(cell["source"])
        
        # Replace 'macrotema' with 'tipo_instituicao'
        source = source.replace("base_revisao['macrotema'] = \"\"", "base_revisao['tipo_instituicao'] = \"\"")
        source = source.replace("'macrotema', 'manter'", "'tipo_instituicao', 'manter'")
        source = source.replace("\"macrotema\":", "\"tipo_instituicao\":")
        source = source.replace("base_revisao[\"macrotema\"]", "base_revisao[\"tipo_instituicao\"]")
        source = source.replace("base[\"macrotema\"]", "base[\"tipo_instituicao\"]")
        source = source.replace("regra[\"macrotema\"]", "regra[\"tipo_instituicao\"]")
        source = source.replace("base.loc[filtro, \"macrotema\"]", "base.loc[filtro, \"tipo_instituicao\"]")
        source = source.replace("base_revisao[['valor_normalizado', 'macrotema'", "base_revisao[['valor_normalizado', 'tipo_instituicao'")
        
        # Replace lines in the cells
        new_source_lines = []
        for line in source.splitlines(True):
            new_source_lines.append(line)
        cell["source"] = new_source_lines

with open("notebooks/03_revisao_instituicoes.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
