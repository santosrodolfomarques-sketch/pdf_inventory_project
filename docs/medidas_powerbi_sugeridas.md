# Medidas DAX sugeridas

```DAX
Qtd Documentos = DISTINCTCOUNT(fato_inventario[id_documento_logico])

Qtd Documentos com Estudo de Futuro =
CALCULATE(
    [Qtd Documentos],
    fato_inventario[aplicou_estudo_futuro] = TRUE()
)

% Documentos com Estudo de Futuro =
DIVIDE([Qtd Documentos com Estudo de Futuro], [Qtd Documentos])

Horizonte Médio = AVERAGE(fato_inventario[horizonte_temporal])

Extensão Média do Horizonte = AVERAGE(fato_inventario[extensao_tempo])

Score Médio de Qualidade = AVERAGE(fato_inventario[score_qualidade])

Qtd para Revisão Manual =
CALCULATE(
    [Qtd Documentos],
    fato_inventario[flag_revisao_manual] = TRUE()
)

Média de Temas por Documento = AVERAGE(fato_inventario[qtd_temas])

Média de Métodos por Documento = AVERAGE(fato_inventario[qtd_metodos])
```

## Hierarquias recomendadas

- Tema: `dim_tema[macrotema]` → `dim_tema[subtema]` → `dim_tema[tema]`
- Metodologia: `dim_metodologia[natureza_metodologia]` → `dim_metodologia[familia_do_metodo]` → `dim_metodologia[tipo_estudo_futuro]`
- Tempo: `dim_tempo[ano_publicacao]` → `dim_tempo[horizonte_temporal]`
- Qualidade: `dim_qualidade[nivel_qualidade]` → `dim_qualidade[motivos_revisao]`
