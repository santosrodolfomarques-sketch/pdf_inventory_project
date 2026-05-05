import json
import os

with open("notebooks/03_revisao_instituicoes.ipynb", 'r', encoding='utf-8') as f:
    nb = json.load(f)

code_blocks = ["def display(*args):\n    for a in args: print(a)\n"]
for cell in nb.get('cells', []):
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        source_lines = []
        for line in source.splitlines():
            if not line.strip().startswith('%') and not line.strip().startswith('!'):
                source_lines.append(line)
        code_blocks.append("\n".join(source_lines))

with open("temp_run_03.py", 'w', encoding='utf-8') as f:
    f.write("\n\n".join(code_blocks))
