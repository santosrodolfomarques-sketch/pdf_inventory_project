# Resumo de Valores Únicos - Tabelas BI Ready

## Dimensoes

### dim_abrangencia.csv

- **Total de Linhas:** 19
- **Colunas:** 3

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_abrangencia | 19 | 0 | 1, 2, 3, ... |
| id_abrangencia | 19 | 0 | abr_04ce26c988c44b59, abr_08bf9b194cb3e3e3, abr_257087001d16406f, ... |
| abrangencia | 19 | 0 | ['Brasil', 'Bacia Amazônica', 'Amazônia', 'Cerrado', 'Mata Atlântica', 'São Paulo', 'Porto Alegre', 'Belo Horizonte', 'Amazonas'], Regional, Estadual (Mato Grosso), ... |

### dim_apoio.csv

- **Total de Linhas:** 1876
- **Colunas:** 16

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_instituicao_apoio | 1876 | 0 | 1, 2, 3, ... |
| id_instituicao_apoio | 1876 | 0 | iap_001915ebc82863ee, iap_004fd2a538452956, iap_007267e1c49f0702, ... |
| instituicao_apoio | 1876 | 0 | Governo do Estado, Université de Grenoble, Universidade Estadual de Londrina (UEL), ... |
| valor_normalizado | 33 | 1843 | Fundação Dom Cabral, PwC, Associação Brasileira de Bioinovação (ABBI), ... |
| tipo_instituicao | 7 | 0 | Não classificado, Terceiro Setor e Sociedade Civil, Governo Federal, ... |
| manter | 2 | 1843 | True |
| observacao | 1 | 1876 |  |
| qtd_ocorrencias | 2 | 1843 | 1.0 |
| origem_instituicao | 1 | 0 | Não classificado |
| nivel_governamental | 1 | 0 | Não informado |
| pais_ou_escopo | 1 | 0 | Não informado |
| acao_recomendada | 1 | 0 | revisar_manual |
| fonte_classificacao | 1 | 0 | não informado |
| qualidade_classificacao | 1 | 0 | Não informada |
| confianca_enriquecimento | 1 | 0 | não informado |
| justificativa | 1 | 1876 |  |

### dim_condicionante.csv

- **Total de Linhas:** 1911
- **Colunas:** 19

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_condicionante | 1911 | 0 | 1, 2, 3, ... |
| id_condicionante | 1911 | 0 | con_00188c1e647d9b69, con_006889970a4ab47c, con_00c0d33128e87c46, ... |
| condicionante | 1911 | 0 | Material exclusivamente para uso interno do Cliente., Mobilização da sociedade, Velocidade das mudanças, ... |
| valor_normalizado | 1898 | 0 | Material exclusivamente para uso interno do Cliente., Mobilização da sociedade, Velocidade das mudanças, ... |
| macrocondicionante | 6 | 0 | Tecnológico, Não classificado, Econômico, ... |
| manter | 1 | 0 | True |
| observacao | 1 | 1911 |  |
| qtd_ocorrencias | 1 | 0 | 1 |
| condicionante_normalizado | 1 | 0 | Não classificado |
| tipo_prospectivo | 1 | 0 | Não classificado |
| categoria_steep | 1 | 0 | Não classificado |
| categoria | 1 | 0 | Não classificado |
| cluster | 1 | 0 | Não classificado |
| horizonte_implicado | 1 | 0 | Não informado |
| direcionalidade | 1 | 0 | Não informado |
| eh_condicionante_prospectivo | 1 | 0 | Revisar |
| confianca_enriquecimento | 1 | 0 | não informado |
| acao_recomendada | 1 | 0 | revisar_manual |
| justificativa | 1 | 1911 |  |

### dim_documento.csv

- **Total de Linhas:** 143
- **Colunas:** 8

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_documento | 143 | 0 | 1, 2, 3, ... |
| id_documento_hash | 143 | 0 | doc_02f4cfa6b83b84de, doc_047f5a151709c0e8, doc_0881f891c17efa0d, ... |
| nome_documento | 137 | 0 | OECD Public Governance Reviews: Uzbekistan, Cenários mundo-Brasil 2030 – insumos para o planejamento estratégico do BNDES, GLOBAL TRENDS TO 2040 Choosing Europe’s future, ... |
| nome_documento_curto | 139 | 0 | OECD Public Governance Reviews: Uzbekistan, Cenários mundo-Brasil 2030 – insumos para o planejamento estratégico do BNDES, GLOBAL TRENDS TO 2040 Choosing Europe’s future, ... |
| sigla_ou_abreviacao | 135 | 0 | OPGRU, CMB2IPEB, GTT2CESF, ... |
| tipo_documento | 34 | 0 | Review, Artigo/Relatório, Relatório, ... |
| instituicao_responsavel | 103 | 0 | Organisation for Economic Co-operation and Development, Banco Nacional de Desenvolvimento Econômico e Social (BNDES), European Strategy and Policy Analysis System, ... |
| qtd_arquivos_origem | 1 | 0 | 1 |

### dim_instituicao_responsavel.csv

- **Total de Linhas:** 103
- **Colunas:** 16

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_instituicao | 103 | 0 | 1, 2, 3, ... |
| id_instituicao | 103 | 0 | ins_006799f210b54c78, ins_031398b112b7f6d3, ins_03eb6f244e5bfb20, ... |
| instituicao | 103 | 0 | Marsh McLennan, Ex Ante Consultoria Econômica, Organisation for Economic Co-operation and Development, ... |
| valor_normalizado | 73 | 30 | Marsh McLennan, EX ANTE CONSULTORIA ECONÔMICA, Organisation for Economic Co-operation and Development, ... |
| tipo_instituicao | 7 | 0 | Não classificado, Governo Federal, Governo Estadual / Distrital, ... |
| manter | 2 | 30 | True |
| observacao | 1 | 103 |  |
| qtd_ocorrencias | 2 | 30 | 1.0 |
| origem_instituicao | 1 | 0 | Não classificado |
| nivel_governamental | 1 | 0 | Não informado |
| pais_ou_escopo | 1 | 0 | Não informado |
| acao_recomendada | 1 | 0 | revisar_manual |
| fonte_classificacao | 1 | 0 | não informado |
| qualidade_classificacao | 1 | 0 | Não informada |
| confianca_enriquecimento | 1 | 0 | não informado |
| justificativa | 1 | 103 |  |

### dim_metodo.csv

- **Total de Linhas:** 562
- **Colunas:** 20

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_metodo | 562 | 0 | 1, 2, 3, ... |
| id_metodo_hash | 562 | 0 | met_002efaa7abde1a5f, met_008ecd341ec919ed, met_01236b2478277fb7, ... |
| metodo | 511 | 0 | Formulação de Hipóteses, Inventário, Coleta de Dados em Bases Públicas, ... |
| familia_do_metodo | 8 | 0 | Cenários Prospectivos, Extrapolação de Tendências, Não classificado, ... |
| natureza_metodo | 5 | 0 | Prospectivo, Não Classificado, Quantitativo, ... |
| metodo_normalizado | 511 | 0 | Formulação de Hipóteses, Inventário, Coleta de Dados em Bases Públicas, ... |
| familia_metodo | 9 | 0 | Cenários Prospectivos, Extrapolação de Tendências, Não classificado, ... |
| manter | 2 | 561 | True |
| observacao | 1 | 562 |  |
| qtd_ocorrencias | 2 | 561 | 1.0 |
| codigo_familia | 1 | 0 | Não classificado |
| codigo_subfamilia | 1 | 0 | Não classificado |
| subfamilia_metodo | 1 | 0 | Não classificado |
| funcao_primaria | 1 | 0 | Não classificado |
| grau_prospectivo | 1 | 0 | Não classificado |
| confianca_enriquecimento | 1 | 0 | não informado |
| acao_recomendada | 1 | 0 | revisar_manual |
| justificativa_metodo | 1 | 562 |  |
| fonte_classificacao | 1 | 0 | não informado |
| qualidade_classificacao | 1 | 0 | Não informada |

### dim_metodologia.csv

- **Total de Linhas:** 56
- **Colunas:** 7

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_metodologia | 56 | 0 | 1, 2, 3, ... |
| id_metodologia_hash | 56 | 0 | mdg_00a955e567010ab1, mdg_058840ca48694957, mdg_07192a6bcdde58e8, ... |
| familia_do_metodo | 7 | 0 | Extrapolação de Tendências, Painel de Especialistas (Delphi/Workshops), Cenários Prospectivos, ... |
| natureza_metodologia | 4 | 0 | Não Classificado, Qualitativo, Prospectivo, ... |
| tipo_estudo_futuro | 46 | 0 | Planejamento Estratégico de Desenvolvimento Digital, Projeção e Análise de Tendências, Planejamento Estratégico Situacional, ... |
| aplicou_estudo_futuro | 2 | 0 | True, False |
| aplicou_estudo_futuro_status | 2 | 0 | Sim, Não |

### dim_qualidade.csv

- **Total de Linhas:** 143
- **Colunas:** 8

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_qualidade | 143 | 0 | 1, 2, 3, ... |
| id_qualidade_hash | 143 | 0 | qlt_0527f201e6303a5c, qlt_0590e211bca3eb4f, qlt_0adc74cabc220d54, ... |
| sk_documento | 143 | 0 | 136, 73, 121, ... |
| id_documento_logico | 143 | 0 | doc_f1f59697542c1626, doc_779f0464baab41f0, doc_ce96322d0ec610cc, ... |
| score_qualidade | 13 | 0 | 1.0, 0.9, 0.63, ... |
| nivel_qualidade | 3 | 0 | Alta, Média, Crítica |
| flag_revisao_manual | 2 | 0 | False, True |
| motivos_revisao | 8 | 118 | setor_nao_informado, ano_publicacao_ausente; estudo_futuro_sem_metodo, ano_publicacao_ausente, ... |

### dim_referencia.csv

- **Total de Linhas:** 4453
- **Colunas:** 3

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_referencia | 4453 | 0 | 1, 2, 3, ... |
| id_referencia | 4453 | 0 | ref_00025ce322d38924, ref_000832e71ae7ff96, ref_001435d56cab1e3d, ... |
| referencia | 4453 | 0 | INSTITUTO TRATA BRASIL (ITB). Ranking do Saneamento 2024., METTENLEITER, T. C.; MARKOTTER, W.; CHARRON, D. F.; LMUHAIRI, A. S.; BEHRAVESH, C. B.; BILIVOGUI, P.; BUKACHI,S. A.; CASAS, N.; BECERRA, N. C.; CHAUDHARY, A.; ZANELLA, J. R. C.; UNNINGHAM,A. A.; DAR, O.; DEBNATH, N.; DUNGU, B.; FARAG, E.; GAO,G. F.; AYMAN, D. T. S.; KHAITSA, M.; KOOPMANS, M. P. G.; MACHALABA, C.; MACKENZIE, J. S.; MORAND, S.; SMOLENSKIY, V.; ZHOU, L. The One Health High-Level Expert Panel (OHHLEP). One Health Outlook, v. 5, n. 18, 2023. DOI: https://doi.org/10.1186/s42522-023-00085-2., Plano Integrado de Longo Prazo da Infraestrutura-PILPI; Comitê Interministerial de Planejamento da Infraestrutura; 2021., ... |

### dim_setor.csv

- **Total de Linhas:** 89
- **Colunas:** 3

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_setor | 89 | 0 | 1, 2, 3, ... |
| id_setor | 89 | 0 | set_01aecadf98af807e, set_02376ef0fb942fcf, set_04790cc1dff0196a, ... |
| setor | 89 | 0 | ['Desenvolvimento Econômico', 'Social', 'Educação', 'Meio Ambiente', 'Infraestrutura', 'Governança'], Economia, Governo, Sociedade, Saúde, Economia, ... |

### dim_source_file.csv

- **Total de Linhas:** 143
- **Colunas:** 3

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_source_file | 143 | 0 | 1, 2, 3, ... |
| id_arquivo_origem | 143 | 0 | src_0181b990298470c1, src_03ad79371059d9cd, src_06d9d090624727c9, ... |
| arquivo_origem | 143 | 0 | 081.pdf, 095.pdf, 064.pdf, ... |

### dim_tema.csv

- **Total de Linhas:** 2257
- **Colunas:** 5

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_tema | 2257 | 0 | 1, 2, 3, ... |
| id_tema_hash | 2257 | 0 | tem_0014d9df8dc729ef, tem_0038c2e35cb88bf0, tem_003aa7e781ceecf0, ... |
| tema | 2257 | 0 | Pluralidade, Blockchain, Políticas Públicas para Catadores, ... |
| macrotema | 18 | 0 | Outros / Revisar, Tecnologia e Inovação, Ciência, Tecnologia e Inovação, ... |
| subtema | 29 | 0 | Revisar Manualmente, Transformação Digital, Tecnologia Digital, ... |

### dim_tempo.csv

- **Total de Linhas:** 85
- **Colunas:** 5

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_tempo | 85 | 0 | 1, 2, 3, ... |
| id_tempo_hash | 85 | 0 | tmp_047fc3e4057aa7d5, tmp_0c1406b4efb3f32a, tmp_0d2e7bcc495a8de0, ... |
| ano_publicacao | 22 | 3 | 2019.0, 2020.0, 2014.0, ... |
| horizonte_temporal | 28 | 9 | 2035.0, 2030.0, 2025.0, ... |
| extensao_tempo | 36 | 11 | 16.0, 10.0, 21.0, ... |

## Fatos

### fato_inventario.csv

- **Total de Linhas:** 143
- **Colunas:** 50

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_fato_inventario | 143 | 0 | 1, 2, 3, ... |
| id_fato_inventario_hash | 143 | 0 | fat_bee6fdc2d964eac0, fat_662b5b5feb8af352, fat_11fc84401d425f2e, ... |
| sk_documento | 143 | 0 | 1, 2, 3, ... |
| id_documento_logico | 143 | 0 | doc_02f4cfa6b83b84de, doc_047f5a151709c0e8, doc_0881f891c17efa0d, ... |
| sk_tempo | 85 | 0 | 14, 32, 78, ... |
| id_tempo_hash | 85 | 0 | tmp_2571dc52b6346c86, tmp_4f98b80d969095db, tmp_df6ea36386de39ec, ... |
| sk_setor | 89 | 0 | 20, 21, 31, ... |
| id_setor | 89 | 0 | set_2f833d5ddb9d513c, set_31fe19d6556d809f, set_4090891c7e59272e, ... |
| sk_abrangencia | 19 | 0 | 8, 13, 5, ... |
| id_abrangencia | 19 | 0 | abr_55e7d4a9a07c954a, abr_a369a600672fd657, abr_33f339d7c580daf0, ... |
| sk_instituicao | 102 | 0 | 3, 86, 22, ... |
| sk_metodologia | 56 | 0 | 18, 19, 45, ... |
| id_metodologia_hash | 56 | 0 | mdg_53506df7ba6a4d32, mdg_553a8471404bc6a5, mdg_c7edeb9becdb8f05, ... |
| sk_qualidade | 143 | 0 | 38, 95, 92, ... |
| id_qualidade_hash | 143 | 0 | qlt_4a0efd49a55312b4, qlt_b24e4909f83980d7, qlt_ace17a876e2817e1, ... |
| ano_publicacao | 22 | 7 | 2024.0, 2015.0, 2023.0, ... |
| horizonte_temporal | 28 | 17 | 2030.0, 2040.0, 2019.0, ... |
| extensao_tempo | 36 | 20 | 6.0, 15.0, 16.0, ... |
| aplicou_estudo_futuro | 2 | 0 | True, False |
| aplicou_estudo_futuro_status | 2 | 0 | Sim, Não |
| qtd_arquivos_origem | 1 | 0 | 1 |
| qtd_temas | 56 | 0 | 92, 15, 12, ... |
| qtd_metodos | 18 | 0 | 1, 10, 3, ... |
| qtd_referencias | 60 | 0 | 79, 8, 144, ... |
| qtd_condicionantes | 38 | 0 | 45, 32, 4, ... |
| qtd_instituicoes_apoio | 49 | 0 | 1, 4, 11, ... |
| densidade_informacional | 87 | 0 | 217, 65, 163, ... |
| possui_condicionantes | 2 | 0 | True, False |
| possui_metodo_identificado | 2 | 0 | True, False |
| possui_horizonte_temporal | 2 | 0 | True, False |
| score_qualidade | 13 | 0 | 1.0, 0.85, 0.88, ... |
| nivel_qualidade | 3 | 0 | Alta, Média, Crítica |
| motivos_revisao | 8 | 118 | estudo_futuro_sem_metodo, ano_publicacao_ausente, setor_nao_informado, ... |
| nome_documento | 137 | 3 | OECD Public Governance Reviews: Uzbekistan, Cenários mundo-Brasil 2030 – insumos para o planejamento estratégico do BNDES, GLOBAL TRENDS TO 2040 Choosing Europe’s future, ... |
| nome_documento_norm | 137 | 3 | OECD Public Governance Reviews: Uzbekistan, Cenários mundo-Brasil 2030 – insumos para o planejamento estratégico do BNDES, GLOBAL TRENDS TO 2040 Choosing Europe’s future, ... |
| nome_documento_curto | 139 | 0 | OECD Public Governance Reviews: Uzbekistan, Cenários mundo-Brasil 2030 – insumos para o planejamento estratégico do BNDES, GLOBAL TRENDS TO 2040 Choosing Europe’s future, ... |
| tipo_documento | 79 | 3 | Review, Artigo/Relatório, Report, ... |
| tipo_documento_norm | 34 | 3 | Review, Artigo/Relatório, Relatório, ... |
| setor | 97 | 12 | Public Administration, Planejamento Estratégico, Desenvolvimento Econômico, Multi-setorial, ... |
| setor_norm | 89 | 12 | Gestão Pública, Desenvolvimento Econômico, Multi-setorial, ... |
| abrangencia_territorial | 54 | 4 | Uzbekistan, Mundo e Brasil, Global, Europe, EU, ... |
| abrangencia_territorial_norm | 19 | 4 | Nacional, Global, Estadual, ... |
| instituicao_responsavel | 115 | 4 | Organisation for Economic Co-operation and Development, Banco Nacional de Desenvolvimento Econômico e Social (BNDES), European Strategy and Policy Analysis System (ESPAS), ... |
| instituicao_responsavel_norm | 103 | 4 | Organisation for Economic Co-operation and Development, Banco Nacional de Desenvolvimento Econômico e Social (BNDES), European Strategy and Policy Analysis System, ... |
| tipo_estudo_futuro | 95 | 7 | Strategic Planning, Cenários, Foresight, Trends Analysis, ... |
| tipo_estudo_futuro_norm | 46 | 7 | Planejamento Estratégico, Cenários Prospectivos, Foresight, ... |
| familia_do_metodo | 1 | 143 |  |
| familia_do_metodo_norm | 7 | 7 | Outros, Cenários Prospectivos, Extrapolação de Tendências, ... |
| source_file_name | 143 | 0 | 046.pdf, 016.pdf, 036.pdf, ... |
| source_file_hash | 143 | 0 | d4d17faa605973cc3088afc01d6031f71aadda0a4dd29e2a6293e032c30e59f0, eab023e851719857710ec667ec4acaef3f6f01f89db477c5ba05374c88ba9a97, 2069cb241b50c9ec8f7cc6ac802626dd93eb55be361864f3e75ceae238f451b2, ... |

## Pontes

### ponte_documento_arquivo_origem.csv

- **Total de Linhas:** 143
- **Colunas:** 4

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_documento | 143 | 0 | 18, 126, 48, ... |
| id_documento_logico | 143 | 0 | doc_166264e608701b27, doc_dd3da919f4ffd49c, doc_49e12d5670dda940, ... |
| sk_source_file | 143 | 0 | 78, 102, 67, ... |
| id_arquivo_origem | 143 | 0 | src_9ef2cc29b4f6403c, src_c41ec0753391352f, src_8e24a769813f54b4, ... |

### ponte_documento_condicionante.csv

- **Total de Linhas:** 1977
- **Colunas:** 4

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_documento | 134 | 0 | 126, 48, 139, ... |
| id_documento_logico | 134 | 0 | doc_dd3da919f4ffd49c, doc_49e12d5670dda940, doc_fa5f7c163878c40b, ... |
| sk_condicionante | 1911 | 0 | 1511, 666, 1352, ... |
| id_condicionante | 1911 | 0 | con_cc908a3d1a49b48d, con_5b800e00402d5143, con_b80f0fd81524eaa5, ... |

### ponte_documento_instituicao_apoio.csv

- **Total de Linhas:** 2945
- **Colunas:** 4

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_documento | 126 | 0 | 18, 126, 48, ... |
| id_documento_logico | 126 | 0 | doc_166264e608701b27, doc_dd3da919f4ffd49c, doc_49e12d5670dda940, ... |
| sk_instituicao_apoio | 1876 | 0 | 61, 577, 901, ... |
| id_instituicao_apoio | 1876 | 0 | iap_09df469b442dcd1e, iap_529583496ba27504, iap_7ce1eda9bdc5d35e, ... |

### ponte_documento_metodo.csv

- **Total de Linhas:** 949
- **Colunas:** 4

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_documento | 124 | 0 | 48, 21, 139, ... |
| id_documento_logico | 124 | 0 | doc_49e12d5670dda940, doc_196accfdd54b1443, doc_fa5f7c163878c40b, ... |
| sk_metodo | 562 | 0 | 113, 269, 89, ... |
| id_metodo_hash | 562 | 0 | met_36082daaaa5c861e, met_761401761dbfdf47, met_2a47c97523de697a, ... |

### ponte_documento_referencia.csv

- **Total de Linhas:** 4527
- **Colunas:** 4

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_documento | 131 | 0 | 18, 126, 48, ... |
| id_documento_logico | 131 | 0 | doc_166264e608701b27, doc_dd3da919f4ffd49c, doc_49e12d5670dda940, ... |
| sk_referencia | 4453 | 0 | 2516, 751, 39, ... |
| id_referencia | 4453 | 0 | ref_90fe83e359b62034, ref_2adf1e214eb30308, ref_01cfa5276b9082fd, ... |

### ponte_documento_tema.csv

- **Total de Linhas:** 3964
- **Colunas:** 4

| Coluna | Valores Únicos | Nulos | Exemplo de Valores |
|---|---|---|---|
| sk_documento | 140 | 0 | 18, 126, 48, ... |
| id_documento_logico | 140 | 0 | doc_166264e608701b27, doc_dd3da919f4ffd49c, doc_49e12d5670dda940, ... |
| sk_tema | 2257 | 0 | 2058, 2030, 1880, ... |
| id_tema_hash | 2257 | 0 | tem_e7db77c9168af2e9, tem_e4ba0f638aa585c7, tem_d401b351175a4fde, ... |

