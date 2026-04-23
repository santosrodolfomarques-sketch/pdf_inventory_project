$pastas = @(
    "data\01_raw\pdfs",
    "data\02_extracted\json_raw",
    "data\02_extracted\logs",
    "data\02_extracted\controle_processamento",
    "data\03_transformed\tabelas_base",
    "data\03_transformed\tabelas_normalizadas",
    "data\03_transformed\pendencias",
    "data\03_transformed\valores_unicos_para_normalizacao",
    "data\04_bi_ready\dimensoes",
    "data\04_bi_ready\fatos",
    "data\04_bi_ready\pontes",
    "data\04_bi_ready\dicionario_dados",
    "src\extraction",
    "src\transformation",
    "src\bi",
    "src\shared"
)

foreach ($pasta in $pastas) {
    New-Item -ItemType Directory -Path $pasta -Force | Out-Null
}

Write-Host "Estrutura criada com sucesso."
