from __future__ import annotations

import json
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np

from src.core.config import get_settings
from src.bi.pipeline import run_bi_preparation
from google import genai

# Configurações iniciais da página Streamlit
st.set_page_config(
    page_title="PDF Inventory Curation Hub",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS premium (Tema escuro, glassmorphism e cores modernas HSL)
st.markdown("""
<style>
    .main {
        background-color: #0f1115;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    .stSidebar {
        background-color: #161920 !important;
        border-right: 1px solid #2d3139;
    }
    h1, h2, h3 {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
    .card {
        background: rgba(22, 25, 32, 0.7);
        border: 1px solid #2d3139;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .btn-save {
        background-color: #0284c7 !important;
        color: white !important;
        border-radius: 6px !important;
    }
</style>
""", unsafe_allow_html=True)

settings = get_settings()


def _reprocess_bi_pipeline():
    """Gera novamente as tabelas do Star Schema com os dados editados ou normalizações salvas."""
    from src.shared.logging_utils import setup_logger
    logger = setup_logger("streamlit_curator", settings.extraction_log_dir / "streamlit_curator.log")
    
    with st.spinner("Atualizando tabelas e integridade do Star Schema BI..."):
        report = run_bi_preparation(settings, logger)
        if report.get("status") == "ok":
            st.success("Tabelas BI atualizadas com sucesso!")
        else:
            st.warning(f"Chaves e integridade recriadas com alguns alertas: {report.get('status')}")


# --- Sidebar de Navegação ---
st.sidebar.title("📚 Curation Hub")
st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "Navegação",
    ["📊 Dashboard Geral", "🔍 Busca Semântica", "📝 Navegador & Editor de Documentos", "🛠️ Dicionários de Normalização"]
)
st.sidebar.markdown("---")
st.sidebar.info("Caminho B - Reestruturação Enterprise com Structured Outputs e Pydantic.")


# --- 1. DASHBOARD GERAL ---
if menu == "📊 Dashboard Geral":
    st.title("📊 Painel Geral de Inventário")
    st.markdown("Visão executiva da qualidade dos metadados extraídos dos PDFs técnicos.")

    consolidated_path = settings.transformed_base_dir / "documentos_consolidados.csv"
    if not consolidated_path.exists():
        st.error("Nenhuma base transformada encontrada. Por favor, execute o pipeline principal.")
    else:
        df = pd.read_csv(consolidated_path)

        # KPIs Rápidos em cartões Premium
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<div class="card"><h3>Total Documentos</h3><h2>{len(df)}</h2></div>', unsafe_allow_html=True)
        with col2:
            estudos_futuro = df["aplicou_estudo_futuro"].astype(str).str.lower().isin(["true", "1", "sim", "yes"]).sum()
            st.markdown(f'<div class="card"><h3>Estudos de Futuro</h3><h2>{estudos_futuro}</h2></div>', unsafe_allow_html=True)
        with col3:
            anos_distintos = df["ano_publicacao"].dropna().nunique()
            st.markdown(f'<div class="card"><h3>Anos de Publicação</h3><h2>{anos_distintos}</h2></div>', unsafe_allow_html=True)
        with col4:
            s_files = df["qtd_arquivos_origem"].sum() if "qtd_arquivos_origem" in df.columns else len(df)
            st.markdown(f'<div class="card"><h3>Arquivos de Origem</h3><h2>{s_files}</h2></div>', unsafe_allow_html=True)

        st.markdown("### 📋 Prévia das Informações Consolidadas")
        st.dataframe(df[["nome_documento", "tipo_documento", "ano_publicacao", "setor", "aplicou_estudo_futuro"]].head(15), use_container_width=True)


# --- 2. BUSCA SEMÂNTICA POR EMBEDDING ---
elif menu == "🔍 Busca Semântica":
    st.title("🔍 Busca Semântica Inteligente")
    st.markdown("Encontre documentos baseando-se em conceitos abstratos, graças aos embeddings gerados via Gemini API.")

    query = st.text_input("Digite sua pergunta ou conceito de busca (Ex: Transição energética e hidrogênio verde):")

    if query:
        # Busca todas as extrações salvas
        extracted_files = sorted(Path(settings.extracted_json_dir).glob("*.json"))
        docs_with_embeddings = []

        for p in extracted_files:
            try:
                with p.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                # Verifica se possui vetor de embedding salvo
                if data.get("embedding") and len(data["embedding"]) > 0:
                    docs_with_embeddings.append({
                        "name": data["metadata"]["source_file_name"],
                        "title": data["payload"]["nome_documento"] or data["metadata"]["source_file_name"],
                        "payload": data["payload"],
                        "embedding": np.array(data["embedding"], dtype=np.float32)
                    })
            except Exception:
                pass

        if not docs_with_embeddings:
            st.warning("Nenhum documento com vetor de embedding gerado foi encontrado no cache.")
        else:
            try:
                # Gera o embedding da consulta do usuário
                client = genai.Client(api_key=settings.gemini_api_key)
                response = client.models.embed_content(
                    model="text-embedding-004",
                    contents=query
                )
                query_vector = np.array(response.embeddings[0].values, dtype=np.float32)

                # Calcula similaridade de cosseno (produto escalar se normalizado)
                results = []
                for doc in docs_with_embeddings:
                    dot_prod = np.dot(query_vector, doc["embedding"])
                    norm_q = np.linalg.norm(query_vector)
                    norm_d = np.linalg.norm(doc["embedding"])
                    similarity = dot_prod / (norm_q * norm_d)
                    results.append({
                        "Arquivo": doc["name"],
                        "Título do Documento": doc["title"],
                        "Setor": doc["payload"]["setor"] or "Não informado",
                        "Ano": doc["payload"]["ano_publicacao"] or "Não informado",
                        "Similaridade": round(float(similarity) * 100, 2)
                    })

                # Ordena pelos mais similares
                df_results = pd.DataFrame(results).sort_values(by="Similaridade", ascending=False)
                
                st.markdown("### 🏆 Melhores Resultados Encontrados")
                st.dataframe(df_results, use_container_width=True)

            except Exception as exc:
                st.error(f"Falha ao chamar a API de Embeddings do Gemini: {exc}")


# --- 3. NAVEGADOR & EDITOR DE DOCUMENTOS ---
elif menu == "📝 Navegador & Editor de Documentos":
    st.title("📝 Navegador & Editor de Documentos")
    st.markdown("Edite de forma interativa e salve alterações de qualquer campo extraído no banco consolidado.")

    consolidated_path = settings.transformed_base_dir / "documentos_consolidados.csv"
    if not consolidated_path.exists():
        st.error("Por favor, execute o pipeline para gerar o arquivo documentos_consolidados.csv.")
    else:
        df = pd.read_csv(consolidated_path)

        # Caixa de seleção do documento
        documentos_disponiveis = df["nome_documento"].dropna().unique().tolist()
        doc_selecionado = st.selectbox("Escolha um documento para auditar e editar:", documentos_disponiveis)

        if doc_selecionado:
            # Obtém a linha correspondente do DataFrame
            idx = df[df["nome_documento"] == doc_selecionado].index[0]
            row = df.loc[idx]

            # Formulário interativo
            with st.form("edit_form"):
                st.subheader(f"Campos Factuais do Documento")
                
                col1, col2 = st.columns(2)
                with col1:
                    nome_doc = st.text_input("Nome do Documento", value=str(row["nome_documento"]))
                    tipo_doc = st.text_input("Tipo do Documento", value=str(row["tipo_documento"]))
                    ano_pub = st.number_input("Ano de Publicação", value=int(row["ano_publicacao"]) if pd.notna(row["ano_publicacao"]) else 2026, step=1)
                    horiz_temp = st.number_input("Horizonte Temporal Target", value=int(row["horizonte_temporal"]) if pd.notna(row["horizonte_temporal"]) else 2030, step=1)
                
                with col2:
                    setor_doc = st.text_input("Setor Primário", value=str(row["setor"]))
                    abrangencia_doc = st.text_input("Abrangência Territorial", value=str(row["abrangencia_territorial"]))
                    inst_resp_doc = st.text_input("Instituição Responsável", value=str(row["instituicao_responsavel"]))
                    aplicou_futuro = st.checkbox("Aplicou Estudo de Futuro / Prospectiva", value=bool(row["aplicou_estudo_futuro"]) if pd.notna(row["aplicou_estudo_futuro"]) else False)

                col3, col4 = st.columns(2)
                with col3:
                    tipo_estudo = st.text_input("Tipo Abordagem de Futuro", value=str(row["tipo_estudo_futuro"]) if pd.notna(row["tipo_estudo_futuro"]) else "")
                    temas_list = st.text_area("Temas Chave (separados por vírgula)", value=", ".join(json.loads(str(row["temas"]))) if str(row["temas"]).startswith("[") else str(row["temas"]))
                    metodos_list = st.text_area("Métodos Utilizados (separados por vírgula)", value=", ".join(json.loads(str(row["metodos_estudo_futuro"]))) if str(row["metodos_estudo_futuro"]).startswith("[") else str(row["metodos_estudo_futuro"]))
                
                with col4:
                    inst_apoio_list = st.text_area("Instituições de Apoio (separados por vírgula)", value=", ".join(json.loads(str(row["instituicoes_apoio"]))) if str(row["instituicoes_apoio"]).startswith("[") else str(row["instituicoes_apoio"]))
                    cond_list = st.text_area("Fatores Condicionantes (separados por vírgula)", value=", ".join(json.loads(str(row["condicionantes_estudo_futuro"]))) if str(row["condicionantes_estudo_futuro"]).startswith("[") else str(row["condicionantes_estudo_futuro"]))
                    refs_list = st.text_area("Referências Bibliográficas (separados por vírgula)", value=", ".join(json.loads(str(row["referencias"]))) if str(row["referencias"]).startswith("[") else str(row["referencias"]))

                submit_btn = st.form_submit_button("Salvar Alterações e Recriar Modelagem BI")

                if submit_btn:
                    # Converte campos de lista de volta para JSON string
                    def to_json_list(text):
                        return json.dumps([item.strip() for item in text.split(",") if item.strip()], ensure_ascii=False)

                    df.at[idx, "nome_documento"] = nome_doc
                    df.at[idx, "tipo_documento"] = tipo_doc
                    df.at[idx, "ano_publicacao"] = ano_pub
                    df.at[idx, "horizonte_temporal"] = horiz_temp
                    df.at[idx, "setor"] = setor_doc
                    df.at[idx, "abrangencia_territorial"] = abrangencia_doc
                    df.at[idx, "instituicao_responsavel"] = inst_resp_doc
                    df.at[idx, "aplicou_estudo_futuro"] = aplicou_futuro
                    df.at[idx, "tipo_estudo_futuro"] = tipo_estudo
                    df.at[idx, "temas"] = to_json_list(temas_list)
                    df.at[idx, "metodos_estudo_futuro"] = to_json_list(metodos_list)
                    df.at[idx, "instituicoes_apoio"] = to_json_list(inst_apoio_list)
                    df.at[idx, "condicionantes_estudo_futuro"] = to_json_list(cond_list)
                    df.at[idx, "referencias"] = to_json_list(refs_list)

                    # Salva no disco
                    df.to_csv(consolidated_path, index=False, encoding="utf-8-sig")
                    
                    # Atualiza o modelo de BI
                    _reprocess_bi_pipeline()


# --- 4. AUDITORIA DE DICIONÁRIOS DE IA ---
elif menu == "🛠️ Dicionários de Normalização":
    st.title("🛠️ Auditoria de Dicionários IA")
    st.markdown("Valide ou edite as normalizações automáticas propostas pela inteligência artificial antes da modelagem final do Power BI.")

    targets = ["setor", "tipo_documento", "abrangencia_territorial", "tipo_estudo_futuro", "instituicao_responsavel", "condicionantes"]
    target_sel = st.selectbox("Selecione o dicionário para auditar:", targets)

    dict_path = settings.ai_dictionary_dir / f"dicionario_{target_sel}.csv"

    if not dict_path.exists():
        st.error(f"Dicionário dicionario_{target_sel}.csv não encontrado no disco.")
    else:
        df_dict = pd.read_csv(dict_path)

        st.subheader(f"Mapeamentos do Dicionário: {target_sel}")

        # Tabela com caixa de seleção de aprovação
        df_dict_editable = st.data_editor(
            df_dict,
            column_config={
                "aplicar_automaticamente": st.column_config.CheckboxColumn(
                    "Aprovado / Aplicar?",
                    help="Se marcado, a normalização será aplicada automaticamente no BI",
                    default=False,
                )
            },
            disabled=["valor_original", "valor_original_limpo"],
            use_container_width=True
        )

        save_dict_btn = st.button("Salvar Dicionário e Re-gerar bases normalizadas")
        if save_dict_btn:
            # Salva no disco
            df_dict_editable.to_csv(dict_path, index=False, encoding="utf-8-sig")
            st.success("Dicionário salvo com sucesso!")

            # Re-aplica as normalizações e atualiza o BI
            from src.normalization.pipeline import apply_ai_dictionaries
            from src.shared.logging_utils import setup_logger
            logger = setup_logger("streamlit_curator", settings.extraction_log_dir / "streamlit_curator.log")
            
            with st.spinner("Atualizando tabelas normalizadas com base nos novos dicionários..."):
                apply_ai_dictionaries(settings, logger)
                _reprocess_bi_pipeline()
