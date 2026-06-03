from __future__ import annotations

import json
import shutil
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import fitz  # PyMuPDF para renderizar capa do PDF

from src.core.config import get_settings
from src.bi.pipeline import run_bi_preparation
from src.extraction.uploader import extract_single_pdf, commit_pdf_to_base
from src.extraction.detector import calculate_document_embedding, find_semantic_duplicates
from src.transformation.pipeline import run_transformation
from src.normalization.pipeline import run_ai_normalization, apply_ai_dictionaries
from src.shared.logging_utils import setup_logger
from google import genai
import logging

class StreamlitLogHandler(logging.Handler):
    """Handler customizado para direcionar logs do logger para um placeholder do Streamlit em tempo real."""
    def __init__(self, placeholder):
        super().__init__()
        self.placeholder = placeholder
        self.log_buffer = []

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_buffer.append(msg)
            # Mantém apenas as últimas 15 linhas de log
            self.log_buffer = self.log_buffer[-15:]
            self.placeholder.code("\n".join(self.log_buffer), language="text")
        except Exception:
            pass

# Configurações iniciais da página Streamlit
st.set_page_config(
    page_title="PDF Inventory Curation Hub",
    page_icon="📚",
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
logger = setup_logger("streamlit_curator", settings.extraction_log_dir / "streamlit_curator.log")


def _reprocess_complete_pipeline():
    """Roda a transformação, normalização e aplicação automática de dicionários."""
    st.markdown("### 🔄 Processando Pipeline...")
    log_placeholder = st.empty()
    st_handler = StreamlitLogHandler(log_placeholder)
    st_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', '%H:%M:%S'))
    logger.addHandler(st_handler)
    try:
        run_transformation(settings, logger)
        run_ai_normalization(settings, logger, only_new_values=True)
        apply_ai_dictionaries(settings, logger)
        st.success("Pipeline atualizado e normalizações aplicadas com sucesso!")
    finally:
        logger.removeHandler(st_handler)


def _reprocess_bi_pipeline():
    """Gera novamente as tabelas do Star Schema com os dados editados ou normalizações salvas."""
    st.markdown("### 📊 Exportando para BI...")
    log_placeholder = st.empty()
    st_handler = StreamlitLogHandler(log_placeholder)
    st_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', '%H:%M:%S'))
    logger.addHandler(st_handler)
    try:
        report = run_bi_preparation(settings, logger)
        if report.get("status") == "ok":
            st.success("Tabelas BI exportadas e salvas com sucesso!")
        else:
            st.warning(f"Chaves e integridade recriadas com alguns alertas: {report.get('status')}")
    finally:
        logger.removeHandler(st_handler)


# --- Sidebar de Navegação ---
st.sidebar.title("📚 Curation Hub")
key_show = settings.gemini_api_key
if key_show:
    masked_key = f"{key_show[:8]}...{key_show[-4:]}"
else:
    masked_key = "⚠️ NÃO DETECTADA"
st.sidebar.caption(f"🔑 Gemini API: `{masked_key}`")
st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "Navegação",
    [
        "📊 Dashboard Geral", 
        "📥 Importar & Processar PDFs", 
        "📄 Ficha do Documento", 
        "📊 Cruzar & Explorar", 
        "🔍 Busca Semântica", 
        "🛠️ Dicionários de Normalização"
    ]
)
st.sidebar.markdown("---")

# Seção de Exportação BI na barra lateral
st.sidebar.subheader("💾 Exportação de Dados")
if st.sidebar.button("Exportar tabelas para BI Ready", use_container_width=True):
    _reprocess_bi_pipeline()

st.sidebar.markdown("---")
st.sidebar.info("Caminho B - Reestruturação Enterprise com Ingestão Incremental e Aprendizado Ativo de Normalização.")


# --- Auxiliar de leitura das bases ---
def load_consolidated_data():
    # Tenta usar a base normalizada por IA se disponível, senão a normal básica
    applied_path = settings.ai_applied_dir / "documentos_consolidados_normalizado_ia.csv"
    base_path = settings.transformed_base_dir / "documentos_consolidados.csv"
    
    path = None
    if applied_path.exists():
        path = applied_path
    elif base_path.exists():
        path = base_path
        
    if path:
        df = pd.read_csv(path)
        for col in ["ano_publicacao", "horizonte_temporal"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
        return df, (path == applied_path)
    return None, False


def get_or_generate_summary(row, pdf_path):
    cache_file = settings.ai_normalization_dir / "resumos_cache.json"
    cache = {}
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            pass
            
    doc_id = str(row.get("id_documento_logico"))
    if doc_id in cache:
        return cache[doc_id]
        
    summary_text = ""
    pdf_text = ""
    if pdf_path and pdf_path.exists():
        try:
            doc_pdf = fitz.open(pdf_path)
            pages = []
            for i in range(min(2, len(doc_pdf))):
                pages.append(doc_pdf[i].get_text("text"))
            pdf_text = "\n".join(pages)
            doc_pdf.close()
        except Exception:
            pass
            
    try:
        client_gen = genai.Client(api_key=settings.gemini_api_key)
        prompt = f"""
        Escreva um resumo executivo muito curto e objetivo (máximo de 3 frases) em português para o seguinte documento técnico.
        Utilize os metadados do documento:
        Título: {row.get('nome_documento')}
        Tipo: {row.get('tipo_documento_norm', row.get('tipo_documento'))}
        Setor: {row.get('setor_norm', row.get('setor'))}
        Temas: {row.get('temas_norm', row.get('temas'))}
        
        Se houver trecho de texto do PDF abaixo, use-o para contextualizar melhor o resumo:
        {pdf_text[:12000]}
        """.strip()
        
        response = client_gen.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )
        summary_text = response.text.strip()
    except Exception as e:
        summary_text = f"Resumo indisponível no momento. (Erro: {e})"
        
    if "indisponível" not in summary_text:
        cache[doc_id] = summary_text
        try:
            settings.ai_normalization_dir.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
            
    return summary_text


# --- 1. DASHBOARD GERAL ---
if menu == "📊 Dashboard Geral":
    st.title("📊 Painel Geral de Inventário")
    st.markdown("Visão executiva da qualidade dos metadados extraídos dos PDFs técnicos.")

    df, is_normalized = load_consolidated_data()
    if df is None:
        st.error("Nenhuma base consolidada encontrada. Por favor, importe PDFs para iniciar.")
    else:
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
        cols_to_show = ["nome_documento", "tipo_documento", "ano_publicacao", "setor", "aplicou_estudo_futuro"]
        if is_normalized and "setor_norm" in df.columns:
            cols_to_show = ["nome_documento", "tipo_documento_norm", "ano_publicacao", "setor_norm", "aplicou_estudo_futuro"]
            
        # Filtra colunas que realmente existem
        cols_to_show = [c for c in cols_to_show if c in df.columns]
        st.dataframe(df[cols_to_show].head(20), use_container_width=True)


# --- 2. INGESTÃO / IMPORTAR & PROCESSAR PDFS ---
elif menu == "📥 Importar & Processar PDFs":
    st.title("📥 Importar e Processar PDFs Incrementalmente")
    st.markdown("Envie novos arquivos PDF técnicos para o pipeline, inspecione duplicados semânticos e confirme a gravação.")

    # Carrega a base consolidada para checar duplicados
    df_consolidated, _ = load_consolidated_data()

    uploaded_files = st.file_uploader("Escolha um ou mais arquivos PDF:", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        temp_dir = settings.raw_pdf_dir / "temp_uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        for uploaded_file in uploaded_files:
            temp_pdf_path = temp_dir / uploaded_file.name
            with open(temp_pdf_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            st.subheader(f"📄 Arquivo: {uploaded_file.name}")
            
            stage_key = f"flow_stage_{uploaded_file.name}"
            stage = st.session_state.get(stage_key)
            
            # Executa a checagem inicial de duplicidade
            if stage is None:
                if st.button(f"Analisar {uploaded_file.name}", key=f"analyze_{uploaded_file.name}"):
                    with st.spinner("Calculando representação semântica e checando duplicidades..."):
                        new_emb = calculate_document_embedding(temp_pdf_path, settings)
                        st.session_state[f"temp_emb_{uploaded_file.name}"] = new_emb
                        
                        dup = None
                        if df_consolidated is not None and not df_consolidated.empty and new_emb:
                            dup = find_semantic_duplicates(new_emb, df_consolidated, settings, threshold=0.85)
                            
                        if dup:
                            st.session_state[f"dup_detected_{uploaded_file.name}"] = dup
                            st.session_state[stage_key] = "conflict_check"
                        else:
                            st.session_state[stage_key] = "normal_extract"
                        st.rerun()
                        
            # Fluxo 1: Duplicado Detectado - Escolha de Ação
            if stage == "conflict_check":
                dup = st.session_state[f"dup_detected_{uploaded_file.name}"]
                st.warning(
                    f"⚠️ **Potencial Duplicado Detectado!**\n\n"
                    f"Este arquivo tem **{dup['similaridade']}%** de similaridade semântica com o documento já cadastrado: "
                    f"**'{dup['nome_documento_duplicado']}'** (arquivo original: `{dup['arquivo_duplicado']}`)."
                )
                
                decision = st.radio(
                    "Como deseja proceder com este arquivo?",
                    [
                        "❌ Descartar este arquivo de upload", 
                        "➕ Inserir como um novo documento independente", 
                        "🤝 Mesclar as informações dos dois documentos (Resolução de Conflitos)"
                    ],
                    key=f"decision_{uploaded_file.name}"
                )
                
                if st.button("Confirmar Opção", key=f"btn_confirm_{uploaded_file.name}"):
                    if decision.startswith("❌"):
                        try:
                            temp_pdf_path.unlink()
                        except Exception:
                            pass
                        st.session_state.pop(stage_key, None)
                        st.session_state.pop(f"dup_detected_{uploaded_file.name}", None)
                        st.session_state.pop(f"temp_emb_{uploaded_file.name}", None)
                        st.success("Upload descartado.")
                        st.rerun()
                    elif decision.startswith("➕"):
                        st.session_state[stage_key] = "normal_extract"
                        st.rerun()
                    elif decision.startswith("🤝"):
                        with st.spinner("Carregando extração multimodal para resolução de conflitos..."):
                            result = extract_single_pdf(temp_pdf_path, settings, logger)
                        if result.get("status") == "success":
                            st.session_state[f"merge_extracted_{uploaded_file.name}"] = result
                            st.session_state[stage_key] = "merge_screen"
                            st.rerun()
                        else:
                            st.error(f"Erro ao extrair metadados para mesclagem: {result.get('error')}")

            # Fluxo 1.1: Tela de Resolução de Conflitos da Mesclagem
            elif stage == "merge_screen":
                dup = st.session_state[f"dup_detected_{uploaded_file.name}"]
                new_record = st.session_state[f"merge_extracted_{uploaded_file.name}"]
                new_payload = new_record["payload"]
                base_data = dup["dados_consolidados"]
                
                st.markdown("### 🤝 Resolução de Conflitos de Metadados")
                st.markdown("Selecione quais valores manter para os campos factuais do documento consolidado:")
                
                resolved_payload = dict(new_payload)
                
                fields_to_resolve = {
                    "nome_documento": "Título do Documento",
                    "tipo_documento": "Tipo de Documento",
                    "setor": "Setor Primário",
                    "abrangencia_territorial": "Abrangência Territorial",
                    "instituicao_responsavel": "Instituição Responsável",
                    "ano_publicacao": "Ano de Publicação",
                    "horizonte_temporal": "Horizonte Temporal",
                    "tipo_estudo_futuro": "Tipo de Abordagem de Futuro"
                }
                
                col_b, col_n = st.columns(2)
                with col_b:
                    st.caption("Dados da Base Consolidada")
                with col_n:
                    st.caption("Dados do Novo PDF")
                    
                resolved_fields = {}
                for field, label in fields_to_resolve.items():
                    val_base = base_data.get(field)
                    val_new = new_payload.get(field)
                    
                    if pd.isna(val_base) or val_base is None:
                        val_base = "Não informado"
                    if pd.isna(val_new) or val_new is None:
                        val_new = "Não informado"
                        
                    if str(val_base).strip().lower() == str(val_new).strip().lower():
                        resolved_fields[field] = val_base
                    else:
                        st.markdown(f"**Campo: {label}**")
                        opt = st.radio(
                            f"Escolha para {label}:",
                            [f"Manter Base: {val_base}", f"Adotar Novo: {val_new}"],
                            key=f"conflict_{field}_{uploaded_file.name}"
                        )
                        resolved_fields[field] = val_base if opt.startswith("Manter") else val_new
                
                if st.button("Confirmar e Salvar Mesclagem", key=f"save_merge_{uploaded_file.name}"):
                    for f, val in resolved_fields.items():
                        if val == "Não informado":
                            val = None
                        elif f in ["ano_publicacao", "horizonte_temporal"] and val is not None:
                            try:
                                val = int(float(val))
                            except ValueError:
                                val = None
                        resolved_payload[f] = val
                    
                    new_record["payload"] = resolved_payload
                    
                    # Salva a nova extração fisicamente e grava no cache
                    new_cache_path = commit_pdf_to_base(temp_pdf_path, new_record, settings, logger)
                    
                    # Atualiza os metadados do documento antigo na pasta de extrações oficiais
                    try:
                        stem_old = Path(dup["arquivo_duplicado"]).stem
                        json_dir = Path(settings.extracted_json_dir)
                        old_caches = list(json_dir.glob(f"{stem_old}__*.json"))
                        if old_caches:
                            with old_caches[0].open("r", encoding="utf-8") as f:
                                old_data = json.load(f)
                            # Alinha os metadados identificadores para garantir o mesmo id_documento_logico
                            for f in ["nome_documento", "ano_publicacao", "instituicao_responsavel"]:
                                old_data["payload"][f] = resolved_payload[f]
                            # Grava de volta
                            write_json(old_caches[0], old_data)
                            logger.info(f"Metadados do cache antigo {old_caches[0].name} atualizados com valores resolvidos da mesclagem.")
                    except Exception as e:
                        logger.error(f"Falha ao atualizar metadados do cache antigo na mesclagem: {e}")
                        
                    _reprocess_complete_pipeline()
                    
                    # Limpa a sessão
                    st.session_state.pop(stage_key, None)
                    st.session_state.pop(f"dup_detected_{uploaded_file.name}", None)
                    st.session_state.pop(f"temp_emb_{uploaded_file.name}", None)
                    st.session_state.pop(f"merge_extracted_{uploaded_file.name}", None)
                    st.success("Mesclagem e consolidação concluídas com sucesso!")
                    st.rerun()

            # Fluxo 2: Processamento Padrão/Inclusão Independente
            elif stage == "normal_extract":
                rec_key = f"temp_record_{uploaded_file.name}"
                if rec_key not in st.session_state:
                    with st.spinner("Extraindo metadados estruturados via Files API do Gemini..."):
                        result = extract_single_pdf(temp_pdf_path, settings, logger)
                        if result.get("status") == "success":
                            st.session_state[rec_key] = result
                        else:
                            st.error(f"Erro ao processar: {result.get('error')}")
                            st.session_state.pop(stage_key, None)
                            st.rerun()
                            
                # Exibe formulário para edição e confirmação
                if rec_key in st.session_state:
                    record = st.session_state[rec_key]
                    payload = record["payload"]
                    
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.markdown("### 🔍 Metadados Extraídos para Revisão")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        nome_doc = st.text_input("Nome do Documento", value=str(payload.get("nome_documento", "")), key=f"name_{uploaded_file.name}")
                        tipo_doc = st.text_input("Tipo de Documento", value=str(payload.get("tipo_documento", "")), key=f"type_{uploaded_file.name}")
                        ano_pub = st.number_input("Ano de Publicação", value=int(payload.get("ano_publicacao")) if payload.get("ano_publicacao") else 2026, step=1, key=f"year_{uploaded_file.name}")
                        horiz_temp = st.number_input("Horizonte Temporal", value=int(payload.get("horizonte_temporal")) if payload.get("horizonte_temporal") else 2030, step=1, key=f"horizon_{uploaded_file.name}")
                    with col2:
                        setor_doc = st.text_input("Setor", value=str(payload.get("setor", "")), key=f"sector_{uploaded_file.name}")
                        abrangencia_doc = st.text_input("Abrangência Territorial", value=str(payload.get("abrangencia_territorial", "")), key=f"scope_{uploaded_file.name}")
                        inst_resp_doc = st.text_input("Instituição Responsável", value=str(payload.get("instituicao_responsavel", "")), key=f"inst_{uploaded_file.name}")
                        aplicou_futuro = st.checkbox("Aplicou Estudo de Futuro / Prospectiva", value=bool(payload.get("aplicou_estudo_futuro", False)), key=f"applied_{uploaded_file.name}")

                    st.markdown("---")
                    col3, col4 = st.columns(2)
                    with col3:
                        tipo_estudo = st.text_input("Tipo Abordagem de Futuro", value=str(payload.get("tipo_estudo_futuro", "")), key=f"tipo_est_{uploaded_file.name}")
                        temas_list = st.text_area("Temas Chave (separados por vírgula)", value=", ".join(payload.get("temas", [])), key=f"temas_{uploaded_file.name}")
                    with col4:
                        metodos_list = st.text_area("Métodos Utilizados (separados por vírgula)", value=", ".join(payload.get("metodos_estudo_futuro", [])), key=f"metodos_{uploaded_file.name}")
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    if st.button(f"Confirmar Inclusão na Base", key=f"commit_{uploaded_file.name}"):
                        def text_to_list(text):
                            return [item.strip() for item in text.split(",") if item.strip()]
                            
                        record["payload"]["nome_documento"] = nome_doc
                        record["payload"]["tipo_documento"] = tipo_doc
                        record["payload"]["ano_publicacao"] = int(ano_pub)
                        record["payload"]["horizonte_temporal"] = int(horiz_temp)
                        record["payload"]["setor"] = setor_doc
                        record["payload"]["abrangencia_territorial"] = abrangencia_doc
                        record["payload"]["instituicao_responsavel"] = inst_resp_doc
                        record["payload"]["aplicou_estudo_futuro"] = aplicou_futuro
                        record["payload"]["tipo_estudo_futuro"] = tipo_estudo
                        record["payload"]["temas"] = text_to_list(temas_list)
                        record["payload"]["metodos_estudo_futuro"] = text_to_list(metodos_list)
                        
                        commit_pdf_to_base(temp_pdf_path, record, settings, logger)
                        _reprocess_complete_pipeline()
                        
                        st.session_state.pop(stage_key, None)
                        st.session_state.pop(rec_key, None)
                        st.session_state.pop(f"temp_emb_{uploaded_file.name}", None)
                        try:
                            temp_pdf_path.unlink()
                        except Exception:
                            pass
                            
                        st.success("Documento incluído com sucesso na base!")
                        st.rerun()


# --- 3. FICHA DO DOCUMENTO (Capa, Resumos e Fatos) ---
elif menu == "📄 Ficha do Documento":
    st.title("📄 Ficha Detalhada do Documento")
    st.markdown("Veja resumos estruturados, termos extraídos e a capa renderizada em tempo real de qualquer PDF cadastrado.")

    df, is_normalized = load_consolidated_data()
    
    if df is None or df.empty:
        st.warning("Nenhum documento encontrado na base consolidada.")
    else:
        # Seletor de documento
        documentos_disponiveis = df["nome_documento"].dropna().unique().tolist()
        doc_selecionado = st.selectbox("Selecione o documento para detalhar:", documentos_disponiveis)
        
        if doc_selecionado:
            row = df[df["nome_documento"] == doc_selecionado].iloc[0]
            
            # Localiza o arquivo PDF físico correspondente na raiz dos dados
            source_files_raw = row.get("source_files", "[]")
            try:
                s_files = json.loads(source_files_raw)
            except Exception:
                s_files = [row["nome_documento"]] if "nome_documento" in row else []
            
            pdf_path = None
            if s_files:
                pdf_path = settings.raw_pdf_dir / s_files[0]
                if not pdf_path.exists():
                    pdf_files = list(settings.raw_pdf_dir.glob("*.pdf"))
                    for p in pdf_files:
                        if p.name.lower() in str(s_files[0]).lower() or str(s_files[0]).lower() in p.name.lower():
                            pdf_path = p
                            break
            
            col_capa, col_info = st.columns([1, 2])
            
            with col_capa:
                st.subheader("🖼️ Capa do Documento")
                pdf_found = False
                if pdf_path and pdf_path.exists():
                    try:
                        # Abre o PDF com PyMuPDF e renderiza a primeira página como imagem
                        doc_pdf = fitz.open(pdf_path)
                        if len(doc_pdf) > 0:
                            page = doc_pdf[0]
                            pix = page.get_pixmap(dpi=130)
                            img_bytes = pix.tobytes("png")
                            st.image(img_bytes, caption=f"Capa de {pdf_path.name}", use_container_width=True)
                            pdf_found = True
                        doc_pdf.close()
                    except Exception as e:
                        st.warning(f"Não foi possível renderizar a capa do PDF: {e}")
                
                if not pdf_found:
                    st.info("Arquivo PDF original não localizado ou impossibilitado de ser renderizado.")

            with col_info:
                st.subheader("📝 Principais Metadados do Documento")
                
                # Exibe dados normalizados prioritariamente se existirem
                setor_val = row.get("setor_norm", row.get("setor", "Não informado"))
                tipo_val = row.get("tipo_documento_norm", row.get("tipo_documento", "Não informado"))
                abrangencia_val = row.get("abrangencia_territorial_norm", row.get("abrangencia_territorial", "Não informado"))
                inst_val = row.get("instituicao_responsavel_norm", row.get("instituicao_responsavel", "Não informado"))
                tipo_estudo_val = row.get("tipo_estudo_futuro_norm", row.get("tipo_estudo_futuro", "Não informado"))
                
                # Renderiza anos como inteiro usando formatação segura
                ano_pub_str = str(row['ano_publicacao']) if pd.notna(row['ano_publicacao']) else 'Não informado'
                horizon_str = str(row['horizonte_temporal']) if pd.notna(row['horizonte_temporal']) else 'Não informado'
                
                st.markdown(f"""
                * **Título:** {row.get('nome_documento')}
                * **Tipo de Documento:** {tipo_val}
                * **Setor:** {setor_val}
                * **Instituição Responsável:** {inst_val}
                * **Ano de Publicação:** {ano_pub_str}
                * **Horizonte Temporal:** {horizon_str}
                * **Abrangência Territorial:** {abrangencia_val}
                * **Estudo de Futuro / Prospectiva?** {'Sim' if str(row.get('aplicou_estudo_futuro')).lower() in ['true', '1', 'sim'] else 'Não'}
                """)
                
                if str(row.get('aplicou_estudo_futuro')).lower() in ['true', '1', 'sim']:
                    st.markdown(f"* **Tipo de Abordagem de Futuro:** {tipo_estudo_val}")
                
                # Aba de Resumo Executivo
                st.markdown("### 📝 Resumo Executivo")
                with st.spinner("Carregando/Gerando resumo executivo do documento..."):
                    resumo_doc = get_or_generate_summary(row, pdf_path)
                st.info(resumo_doc)

                st.markdown("### 🏷️ Categorizações e Listas")
                
                def render_json_list(label, field_name):
                    val_raw = row.get(field_name, "[]")
                    try:
                        # Suporta desserialização flexível (JSON ou ast)
                        import ast
                        items = ast.literal_eval(val_raw) if isinstance(val_raw, str) and val_raw.startswith("[") else val_raw
                        if not isinstance(items, list):
                            items = [items] if pd.notna(items) and items != "" else []
                    except Exception:
                        try:
                            items = json.loads(val_raw)
                        except Exception:
                            items = [val_raw] if pd.notna(val_raw) and val_raw != "" else []
                    
                    if items:
                        st.markdown(f"**{label}:**")
                        cols = st.columns(4)
                        for i, item in enumerate(items):
                            cols[i % 4].markdown(f"🔹 {item}")
                    else:
                        st.markdown(f"**{label}:** *Nenhum identificado*")
                
                render_json_list("Temas Identificados", "temas_norm" if "temas_norm" in row else "temas")
                st.markdown(" ")
                render_json_list("Métodos Utilizados", "metodos_estudo_futuro_norm" if "metodos_estudo_futuro_norm" in row else "metodos_estudo_futuro")
                st.markdown(" ")
                render_json_list("Condicionantes & Incertezas", "condicionantes_estudo_futuro_norm" if "condicionantes_estudo_futuro_norm" in row else "condicionantes_estudo_futuro")
                st.markdown(" ")
                render_json_list("Instituições de Apoio", "instituicoes_apoio_norm" if "instituicoes_apoio_norm" in row else "instituicoes_apoio")

                # --- Reprocessamento de Metadados ---
                st.markdown("---")
                st.markdown("### 🔄 Reprocessamento de Metadados")
                
                reprocess_state_key = f"reprocess_state_{doc_selecionado}"
                reprocess_state = st.session_state.get(reprocess_state_key)
                
                if reprocess_state is None:
                    if not pdf_path or not pdf_path.exists():
                        st.warning("⚠️ O arquivo PDF original não foi encontrado para permitir o reprocessamento.")
                    else:
                        st.markdown("Caso não esteja satisfeito com a extração dos metadados ou queira forçar uma reanálise completa via IA:")
                        if st.button("Reprocessar Documento via Gemini API", key=f"btn_reprocess_{doc_selecionado}"):
                            st.session_state[reprocess_state_key] = "running"
                            st.rerun()
                
                elif reprocess_state == "running":
                    with st.spinner("Conectando à Files API do Gemini e reprocessando o documento físico..."):
                        try:
                            result = extract_single_pdf(pdf_path, settings, logger)
                            if result.get("status") == "success":
                                st.session_state[f"reprocess_record_{doc_selecionado}"] = result
                                st.session_state[reprocess_state_key] = "review"
                                st.success("Nova extração concluída com sucesso! Revise os dados abaixo.")
                            else:
                                st.error(f"Falha na extração: {result.get('error')}")
                                st.session_state[reprocess_state_key] = None
                        except Exception as e:
                            st.error(f"Erro inesperado no reprocessamento: {e}")
                            st.session_state[reprocess_state_key] = None
                    st.rerun()

                elif reprocess_state == "review":
                    record = st.session_state.get(f"reprocess_record_{doc_selecionado}")
                    if record and "payload" in record:
                        payload = record["payload"]
                        
                        st.markdown('<div style="background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.1); margin-top: 10px;">', unsafe_allow_html=True)
                        st.markdown("#### 📝 Revisar Novos Metadados Extraídos")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            nome_doc = st.text_input("Nome do Documento", value=str(payload.get("nome_documento", "")), key=f"rep_name_{doc_selecionado}")
                            tipo_doc = st.text_input("Tipo de Documento", value=str(payload.get("tipo_documento", "")), key=f"rep_type_{doc_selecionado}")
                            ano_pub = st.number_input("Ano de Publicação", value=int(payload.get("ano_publicacao")) if payload.get("ano_publicacao") else 2026, step=1, key=f"rep_year_{doc_selecionado}")
                            horiz_temp = st.number_input("Horizonte Temporal", value=int(payload.get("horizonte_temporal")) if payload.get("horizonte_temporal") else 2030, step=1, key=f"rep_horizon_{doc_selecionado}")
                        with col2:
                            setor_doc = st.text_input("Setor", value=str(payload.get("setor", "")), key=f"rep_sector_{doc_selecionado}")
                            abrangencia_doc = st.text_input("Abrangência Territorial", value=str(payload.get("abrangencia_territorial", "")), key=f"rep_scope_{doc_selecionado}")
                            inst_resp_doc = st.text_input("Instituição Responsável", value=str(payload.get("instituicao_responsavel", "")), key=f"rep_inst_{doc_selecionado}")
                            aplicou_futuro = st.checkbox("Aplicou Estudo de Futuro / Prospectiva", value=bool(payload.get("aplicou_estudo_futuro", False)), key=f"rep_applied_{doc_selecionado}")

                        st.markdown("---")
                        col3, col4 = st.columns(2)
                        with col3:
                            tipo_estudo = st.text_input("Tipo Abordagem de Futuro", value=str(payload.get("tipo_estudo_futuro", "")), key=f"rep_tipo_est_{doc_selecionado}")
                            temas_list = st.text_area("Temas Chave (separados por vírgula)", value=", ".join(payload.get("temas", [])), key=f"rep_temas_{doc_selecionado}")
                        with col4:
                            metodos_list = st.text_area("Métodos Utilizados (separados por vírgula)", value=", ".join(payload.get("metodos_estudo_futuro", [])), key=f"rep_metodos_{doc_selecionado}")
                            condicionantes_list = st.text_area("Condicionantes (separados por vírgula)", value=", ".join(payload.get("condicionantes_estudo_futuro", [])), key=f"rep_conds_{doc_selecionado}")
                            inst_apoio_list = st.text_area("Instituições de Apoio (separados por vírgula)", value=", ".join(payload.get("instituicoes_apoio", [])), key=f"rep_inst_ap_{doc_selecionado}")
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        col_actions = st.columns(2)
                        with col_actions[0]:
                            if st.button("Confirmar e Atualizar Base", key=f"rep_commit_{doc_selecionado}", type="primary"):
                                def text_to_list(text):
                                    return [item.strip() for item in text.split(",") if item.strip()]
                                    
                                record["payload"]["nome_documento"] = nome_doc
                                record["payload"]["tipo_documento"] = tipo_doc
                                record["payload"]["ano_publicacao"] = int(ano_pub)
                                record["payload"]["horizonte_temporal"] = int(horiz_temp)
                                record["payload"]["setor"] = setor_doc
                                record["payload"]["abrangencia_territorial"] = abrangencia_doc
                                record["payload"]["instituicao_responsavel"] = inst_resp_doc
                                record["payload"]["aplicou_estudo_futuro"] = aplicou_futuro
                                record["payload"]["tipo_estudo_futuro"] = tipo_estudo
                                record["payload"]["temas"] = text_to_list(temas_list)
                                record["payload"]["metodos_estudo_futuro"] = text_to_list(metodos_list)
                                record["payload"]["condicionantes_estudo_futuro"] = text_to_list(condicionantes_list)
                                record["payload"]["instituicoes_apoio"] = text_to_list(inst_apoio_list)
                                
                                commit_pdf_to_base(pdf_path, record, settings, logger)
                                _reprocess_complete_pipeline()
                                
                                st.session_state.pop(reprocess_state_key, None)
                                st.session_state.pop(f"reprocess_record_{doc_selecionado}", None)
                                
                                st.success("Documento reprocessado e base atualizada com sucesso!")
                                st.rerun()
                                
                        with col_actions[1]:
                            if st.button("Cancelar", key=f"rep_cancel_{doc_selecionado}"):
                                st.session_state.pop(reprocess_state_key, None)
                                st.session_state.pop(f"reprocess_record_{doc_selecionado}", None)
                                st.rerun()


# --- 4. CRUZAR & EXPLORAR (Análises Internas) ---
elif menu == "📊 Cruzar & Explorar":
    st.title("📊 Cruzar & Explorar Categorizações")
    st.markdown("Gere tabelas dinâmicas de cruzamento e gráficos analíticos diretamente no painel a partir da base consolidada.")

    df, is_normalized = load_consolidated_data()
    
    if df is None or df.empty:
        st.warning("Nenhuma base consolidada encontrada.")
    else:
        # Helper para tratamento e explosão de dimensões
        def prepare_exploded_dimension(df_in, field, dict_name=None, use_category=False, use_subcategory=False):
            from src.transformation.cleansing import remove_accents
            import ast
            import json
            
            # Carrega mapeamentos do dicionário de normalização, se houver
            mapping_dict = {}
            if dict_name:
                dict_path = settings.ai_dictionary_dir / f"dicionario_{dict_name}.csv"
                if dict_path.exists():
                    try:
                        dict_df = pd.read_csv(dict_path)
                        for _, r in dict_df.iterrows():
                            orig = str(r.get("valor_original", "")).strip().lower()
                            norm = str(r.get("valor_normalizado", r.get("valor_original", ""))).strip()
                            cat = str(r.get("categoria", "")).strip()
                            subcat = str(r.get("subcategoria", "")).strip()
                            
                            val_to_use = norm
                            if use_category and cat:
                                val_to_use = cat
                            elif use_subcategory and subcat:
                                val_to_use = subcat
                                
                            if val_to_use:
                                mapping_dict[orig] = val_to_use
                                if norm:
                                    mapping_dict[norm.lower()] = val_to_use
                    except Exception:
                        pass

            def parse_and_map(val):
                if pd.isna(val) or val is None:
                    return ["Não Informado"]
                val_str = str(val).strip()
                if not val_str or val_str.lower() in {"nan", "none", "null", "[]"}:
                    return ["Não Informado"]
                
                # Desserializa se for lista em formato string
                items = []
                if val_str.startswith("[") and val_str.endswith("]"):
                    try:
                        parsed = ast.literal_eval(val_str)
                        if isinstance(parsed, list):
                            items = [str(x).strip() for x in parsed if str(x).strip()]
                    except Exception:
                        try:
                            parsed = json.loads(val_str)
                            if isinstance(parsed, list):
                                items = [str(x).strip() for x in parsed if str(x).strip()]
                        except Exception:
                            pass
                
                if not items:
                    # Divide por vírgula para strings com múltiplos valores
                    items = [x.strip() for x in val_str.split(",") if x.strip()]
                    
                if not items:
                    return ["Não Informado"]
                    
                # Mapeia para dicionário se aplicável
                mapped_items = []
                for item in items:
                    item_key = item.lower()
                    if mapping_dict:
                        mapped_val = mapping_dict.get(item_key, item)
                        if mapped_val and str(mapped_val).lower() not in {"nan", "none", "null", ""}:
                            mapped_items.append(str(mapped_val).strip())
                        else:
                            mapped_items.append(item)
                    else:
                        mapped_items.append(item)
                
                # Remove duplicados
                seen = set()
                unique_items = []
                for x in mapped_items:
                    x_clean = remove_accents(x).lower()
                    if x_clean not in seen:
                        seen.add(x_clean)
                        unique_items.append(x)
                return unique_items if unique_items else ["Não Informado"]

            return df_in[field].apply(parse_and_map)

        st.subheader("🔀 Tabela Cruzada de Dimensões (Explodida)")
        st.markdown(
            "Selecione as dimensões para cruzamento. Os múltiplos valores de campos com listas (ex: setores, temas, métodos) "
            "são automaticamente explodidos para contar as ocorrências individualmente."
        )

        # Mapeia colunas e especificações
        available_dims = {
            "Setor (Normalizado)": {"field": "setor_norm" if "setor_norm" in df.columns else "setor", "dict": "setor"},
            "Setor (Macro Setor - STEEPV)": {"field": "setor_norm" if "setor_norm" in df.columns else "setor", "dict": "setor", "use_category": True},
            "Tipo de Documento": {"field": "tipo_documento_norm" if "tipo_documento_norm" in df.columns else "tipo_documento", "dict": "tipo_documento"},
            "Abrangência Territorial": {"field": "abrangencia_territorial_norm" if "abrangencia_territorial_norm" in df.columns else "abrangencia_territorial", "dict": "abrangencia_territorial"},
            "Temas (Normalizado)": {"field": "temas_norm" if "temas_norm" in df.columns else "temas", "dict": "temas"},
            "Temas (Macrotema - STEEPV)": {"field": "temas_norm" if "temas_norm" in df.columns else "temas", "dict": "temas", "use_category": True},
            "Métodos (Normalizado)": {"field": "metodos_estudo_futuro_norm" if "metodos_estudo_futuro_norm" in df.columns else "metodos_estudo_futuro", "dict": "metodos"},
            "Métodos (Categoria - Popper Foresight Diamond)": {"field": "metodos_estudo_futuro_norm" if "metodos_estudo_futuro_norm" in df.columns else "metodos_estudo_futuro", "dict": "metodos", "use_category": True},
            "Métodos (Subcategoria - Natureza)": {"field": "metodos_estudo_futuro_norm" if "metodos_estudo_futuro_norm" in df.columns else "metodos_estudo_futuro", "dict": "metodos", "use_subcategory": True},
            "Condicionantes (Normalizado)": {"field": "condicionantes_estudo_futuro_norm" if "condicionantes_estudo_futuro_norm" in df.columns else "condicionantes_estudo_futuro", "dict": "condicionantes"},
            "Condicionantes (Categoria - Dimensão STEEPV)": {"field": "condicionantes_estudo_futuro_norm" if "condicionantes_estudo_futuro_norm" in df.columns else "condicionantes_estudo_futuro", "dict": "condicionantes", "use_category": True},
            "Ano de Publicação": {"field": "ano_publicacao"},
            "Horizonte Temporal": {"field": "horizonte_temporal"}
        }

        col_row, col_col = st.columns(2)
        with col_row:
            row_dim = st.selectbox("Dimensão das Linhas (Y):", list(available_dims.keys()), index=1) # Default Setor (Macro Setor - STEEPV)
        with col_col:
            col_dim = st.selectbox("Dimensão das Colunas (X):", list(available_dims.keys()), index=7) # Default Métodos (Categoria - Popper Foresight Diamond)

        if row_dim == col_dim:
            st.error("Por favor, selecione dimensões diferentes para as linhas e colunas.")
        else:
            # 1. Prepara dados limpos e explodidos
            row_spec = available_dims[row_dim]
            col_spec = available_dims[col_dim]
            
            temp_df = df.copy()
            temp_df["_row_val"] = prepare_exploded_dimension(
                df, 
                row_spec["field"], 
                row_spec.get("dict"), 
                row_spec.get("use_category", False), 
                row_spec.get("use_subcategory", False)
            )
            temp_df["_col_val"] = prepare_exploded_dimension(
                df, 
                col_spec["field"], 
                col_spec.get("dict"), 
                col_spec.get("use_category", False), 
                col_spec.get("use_subcategory", False)
            )
            
            # Explode ambas para calcular pares e reseta o índice para evitar índices duplicados
            exploded_df = temp_df.explode("_row_val").explode("_col_val").reset_index(drop=True)
            
            # Remove valores que sejam puramente vazios ou nan após tratamento
            exploded_df["_row_val"] = exploded_df["_row_val"].fillna("Não Informado").astype(str).str.strip()
            exploded_df["_col_val"] = exploded_df["_col_val"].fillna("Não Informado").astype(str).str.strip()
            exploded_df = exploded_df[(exploded_df["_row_val"] != "") & (exploded_df["_col_val"] != "")]

            # Cria pivot table de contagem
            pivot_df = pd.crosstab(
                exploded_df["_row_val"], 
                exploded_df["_col_val"], 
                margins=True, 
                margins_name="Total Geral"
            )
            
            # Exibe tabela no Streamlit
            st.dataframe(pivot_df, use_container_width=True)

            # --- Gráficos do Cruzamento Específico ---
            st.subheader(f"📈 Gráfico Analítico: {row_dim} vs {col_dim}")
            
            # Prepara dados do gráfico tirando o Total Geral para não poluir
            graph_data = pd.crosstab(exploded_df["_row_val"], exploded_df["_col_val"])
            
            # Opções de visualização para o usuário
            chart_type = st.radio(
                "Tipo de Gráfico:", 
                ["Barras Empilhadas (Stacked)", "Barras Agrupadas (Grouped)"], 
                horizontal=True,
                key="chart_type_selector"
            )
            
            if not graph_data.empty:
                st.bar_chart(graph_data, stack=(chart_type == "Barras Empilhadas (Stacked)"))
            else:
                st.info("Dados insuficientes para gerar o gráfico de cruzamento.")

        # --- Seções auxiliares de frequência ---
        st.subheader("📊 Distribuição de Frequências Individuais")
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            st.markdown("#### Distribuição de Anos de Publicação")
            df_year = df["ano_publicacao"].dropna().value_counts().sort_index().reset_index()
            df_year.columns = ["Ano", "Quantidade de Documentos"]
            st.bar_chart(df_year.set_index("Ano"), y="Quantidade de Documentos")
            
        with col_f2:
            st.markdown("#### Top 15 Temas Frequentes")
            temas_list = []
            theme_col = "temas_norm" if "temas_norm" in df.columns else "temas"
            for idx, r in df.iterrows():
                t_raw = r.get(theme_col, "[]")
                try:
                    import ast
                    items = ast.literal_eval(t_raw) if isinstance(t_raw, str) and t_raw.startswith("[") else t_raw
                    if isinstance(items, list):
                        temas_list.extend([str(x).strip() for x in items])
                    else:
                        items_json = json.loads(t_raw) if isinstance(t_raw, str) else [t_raw]
                        temas_list.extend([str(x).strip() for x in items_json])
                except Exception:
                    if pd.notna(t_raw) and t_raw != "":
                        temas_list.extend([x.strip() for x in str(t_raw).split(",") if x.strip()])
            
            if temas_list:
                df_temas = pd.Series(temas_list).value_counts().reset_index()
                df_temas.columns = ["Tema", "Frequência"]
                st.bar_chart(df_temas.head(15).set_index("Tema"), y="Frequência")
            else:
                st.info("Nenhum tema identificado para gerar gráfico.")


# --- 5. BUSCA SEMÂNTICA POR EMBEDDING ---
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
                    model="gemini-embedding-2",
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


# --- 6. AUDITORIA DE DICIONÁRIOS DE IA ---
elif menu == "🛠️ Dicionários de Normalização":
    st.title("🛠️ Auditoria de Dicionários IA")
    st.markdown("Valide ou edite as normalizações propostas pela inteligência artificial e aprendizado ativo.")

    targets = ["setor", "tipo_documento", "abrangencia_territorial", "tipo_estudo_futuro", "instituicao_responsavel", "condicionantes", "temas", "metodos"]
    target_sel = st.selectbox("Selecione o dicionário para auditar:", targets)

    dict_path = settings.ai_dictionary_dir / f"dicionario_{target_sel}.csv"

    if not dict_path.exists():
        st.error(f"Dicionário dicionario_{target_sel}.csv não encontrado no disco.")
    else:
        df_dict = pd.read_csv(dict_path)

        st.subheader(f"Mapeamentos do Dicionário: {target_sel}")

        # Tabela com caixa de seleção de aprovação e exibição de origem
        column_config = {
            "aplicar_automaticamente": st.column_config.CheckboxColumn(
                "Aprovado / Aplicar?",
                help="Se marcado, a normalização será aplicada automaticamente",
                default=False,
            )
        }
        if "origem" in df_dict.columns:
            column_config["origem"] = st.column_config.TextColumn("Origem/Método", disabled=True)

        df_dict_editable = st.data_editor(
            df_dict,
            column_config=column_config,
            disabled=["valor_original", "valor_original_limpo", "origem"] if "origem" in df_dict.columns else ["valor_original", "valor_original_limpo"],
            use_container_width=True
        )

        save_dict_btn = st.button("Salvar Dicionário e Re-gerar bases normalizadas")
        if save_dict_btn:
            # Salva no disco
            df_dict_editable.to_csv(dict_path, index=False, encoding="utf-8-sig")
            st.success("Dicionário salvo com sucesso!")

            # Re-aplica as normalizações
            with st.spinner("Atualizando tabelas normalizadas com base nos novos dicionários..."):
                apply_ai_dictionaries(settings, logger)
                st.success("Bases normalizadas atualizadas!")

        # --- Reprocessamento e Manutenção do Pipeline (Sem Releitura de PDFs) ---
        st.markdown("---")
        st.subheader("🔄 Reprocessamento e Manutenção do Pipeline")
        st.markdown(
            "Como os metadados de todos os PDFs já processados são salvos em cache local (`data/02_extracted/json_raw`), "
            "você pode reexecutar e atualizar as normalizações e taxonomias científicas (STEEPV & Popper Foresight Diamond) "
            "a qualquer momento. **Isso não faz nenhuma chamada para ler os PDFs novamente na API.**"
        )
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown("#### ⚡ Ações Globais Rápidas (Locais)")
            if st.button("Reconstruir Toda a Base (Rápido - Caches Locais)", key="btn_rebuild_all_cache", use_container_width=True):
                st.markdown("##### ⚙️ Executando...")
                log_placeholder = st.empty()
                st_handler = StreamlitLogHandler(log_placeholder)
                st_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', '%H:%M:%S'))
                logger.addHandler(st_handler)
                try:
                    run_transformation(settings, logger)
                    apply_ai_dictionaries(settings, logger)
                    st.success("Toda a base consolidada foi reconstruída a partir dos caches locais!")
                finally:
                    logger.removeHandler(st_handler)
                st.rerun()
                
            if st.button("Buscar e Normalizar Novos Termos via IA", key="btn_norm_new_llm", use_container_width=True):
                st.markdown("##### ⚙️ Executando...")
                log_placeholder = st.empty()
                st_handler = StreamlitLogHandler(log_placeholder)
                st_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', '%H:%M:%S'))
                logger.addHandler(st_handler)
                try:
                    run_transformation(settings, logger)
                    run_ai_normalization(settings, logger, only_new_values=True)
                    apply_ai_dictionaries(settings, logger)
                    st.success("Novos termos classificados via IA e base atualizada!")
                finally:
                    logger.removeHandler(st_handler)
                st.rerun()

        with col_m2:
            st.markdown("#### 🧠 Forçar Recategorização Completa")
            if st.button("Forçar Re-normalização de TODOS os Termos via IA", key="btn_force_llm_all", use_container_width=True):
                st.warning("⚠️ Isso enviará todos os termos únicos da base para reclassificação (STEEPV/Popper's Diamond) via Gemini API.")
                st.markdown("##### ⚙️ Executando...")
                log_placeholder = st.empty()
                st_handler = StreamlitLogHandler(log_placeholder)
                st_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', '%H:%M:%S'))
                logger.addHandler(st_handler)
                try:
                    run_transformation(settings, logger)
                    run_ai_normalization(settings, logger, only_new_values=False)
                    apply_ai_dictionaries(settings, logger)
                    st.success("Todos os termos foram recategorizados via IA!")
                finally:
                    logger.removeHandler(st_handler)
                st.rerun()
