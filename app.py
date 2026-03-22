import streamlit as st
import requests
import json
import io
import time
from datetime import datetime
from duckduckgo_search import DDGS
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
import os

# ─── STORAGE CONFIG ───────────────────────────────────────────────────────────
PROPOSALS_DIR = "data"
PROPOSALS_FILE = os.path.join(PROPOSALS_DIR, "proposals.json")

def ensure_storage():
    if not os.path.exists(PROPOSALS_DIR):
        os.makedirs(PROPOSALS_DIR)
    if not os.path.exists(PROPOSALS_FILE):
        with open(PROPOSALS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

def load_proposals():
    ensure_storage()
    try:
        with open(PROPOSALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_proposal(entry: dict):
    proposals = load_proposals()
    proposals.insert(0, entry) # Newest first
    with open(PROPOSALS_FILE, "w", encoding="utf-8") as f:
        json.dump(proposals, f, indent=4, ensure_ascii=False)

def get_relevant_context(query: str, limit: int = 3) -> str:
    proposals = load_proposals()
    if not proposals: return ""
    
    # Simple keyword matching for "learning"
    relevant = []
    query_words = set(query.lower().split())
    
    for p in proposals:
        score = 0
        p_text = (p.get("title", "") + " " + p.get("desc", "") + " " + p.get("keywords", "")).lower()
        for word in query_words:
            if len(word) > 3 and word in p_text:
                score += 1
        if score > 0:
            relevant.append((score, p))
            
    relevant.sort(key=lambda x: x[0], reverse=True)
    
    context_str = ""
    if relevant:
        context_str = "\n\nCONHECIMENTO PRÉVIO (PROPOSTAS ANTERIORES RELACIONADAS):\n"
        for _, p in relevant[:limit]:
            context_str += f"- Proposta para {p.get('client','Cliente')}: {p.get('title','Sem título')}. Contexto: {p.get('desc','')[:200]}...\n"
            
    return context_str

# ─── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Briefr",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── THEME CONFIG ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-label">Preferências</div>', unsafe_allow_html=True)
    light_mode = st.toggle("Modo Claro", value=False)

# ─── CUSTOM CSS ────────────────────────────────────────────────────────────────
if light_mode:
    # LIGHT MODE COLORS
    bg_app      = "#fcfcfc"
    bg_sidebar  = "#f5f5f7"
    text_main   = "#1d1d1f"
    text_sub    = "#86868b"
    card_bg     = "#ffffff"
    card_border = "#e5e5e7"
    input_bg    = "#ffffff"
    input_border= "#d2d2d7"
    gold        = "#c9a96e"
else:
    # DARK MODE COLORS
    bg_app      = "#0d0d0f"
    bg_sidebar  = "#111114"
    text_main   = "#e8e3d8"
    text_sub    = "#6b6b78"
    card_bg     = "#111114"
    card_border = "#1e1e24"
    input_bg    = "#111114"
    input_border= "#2a2a32"
    gold        = "#c9a96e"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'DM Sans', sans-serif;
}}

.stApp {{
    background: {bg_app};
    color: {text_main};
}}

[data-testid="stSidebar"] {{
    background: {bg_sidebar} !important;
    border-right: 1px solid {card_border};
}}

.hero-title {{
    font-family: 'DM Serif Display', serif;
    font-size: 3.2rem;
    font-weight: 400;
    color: {text_main};
    line-height: 1.1;
    margin: 0;
    letter-spacing: -0.02em;
}}

.hero-title em {{
    font-style: italic;
    color: {gold};
}}

.hero-sub {{
    font-size: 1.05rem;
    color: {text_sub};
    font-weight: 300;
    margin-top: 0.6rem;
    letter-spacing: 0.01em;
}}

.section-label {{
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: {gold};
    margin-bottom: 0.5rem;
}}

.card {{
    background: {card_bg};
    border: 1px solid {card_border};
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    { "box-shadow: 0 4px 20px rgba(0,0,0,0.04);" if light_mode else "" }
}}

.ref-card {{
    background: {card_bg};
    border: 1px solid {card_border};
    border-left: 3px solid {gold};
    border-radius: 0 8px 8px 0;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.7rem;
}}

.ref-title {{
    font-size: 0.88rem;
    font-weight: 500;
    color: {text_main};
    margin: 0 0 0.2rem;
}}

.ref-url {{
    font-size: 0.72rem;
    color: {text_sub};
    margin: 0;
    word-break: break-all;
}}

.ref-body {{
    font-size: 0.8rem;
    color: {text_sub if light_mode else "#9b9aa6"};
    margin-top: 0.35rem;
    line-height: 1.5;
}}

.status-pill {{
    display: inline-block;
    padding: 0.2rem 0.8rem;
    border-radius: 100px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}}

.pill-ok   {{ background: {"#e6f4ea" if light_mode else "#0a2a1a"}; color: {"#1e8e3e" if light_mode else "#4ade80"}; border: 1px solid {"#ceead6" if light_mode else "#166534"}; }}
.pill-warn {{ background: {"#fef7e0" if light_mode else "#2a1a0a"}; color: {"#b06000" if light_mode else "#fb923c"}; border: 1px solid {"#feefc3" if light_mode else "#7c2d12"}; }}
.pill-info {{ background: {"#e8f0fe" if light_mode else "#0a1a2a"}; color: {"#1967d2" if light_mode else "#60a5fa"}; border: 1px solid {"#d2e3fc" if light_mode else "#1e3a5f"}; }}

.proposal-box {{
    background: {card_bg};
    border: 1px solid {card_border};
    border-radius: 12px;
    padding: 2rem 2.4rem;
    font-size: 0.92rem;
    line-height: 1.85;
    color: {text_main};
    white-space: pre-wrap;
    { "box-shadow: 0 8px 32px rgba(0,0,0,0.06);" if light_mode else "" }
}}

.divider {{
    border: none;
    border-top: 1px solid {card_border};
    margin: 1.8rem 0;
}}

/* Streamlit widget overrides */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {{
    background: {input_bg} !important;
    border: 1px solid {input_border} !important;
    color: {text_main} !important;
    border-radius: 8px !important;
}}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {{
    border-color: {gold} !important;
    box-shadow: 0 0 0 2px rgba(201,169,110,0.15) !important;
}}

.stButton > button {{
    background: {gold} !important;
    color: {"#ffffff" if light_mode else "#0d0d0f"} !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.5rem 1.4rem !important;
    font-family: 'DM Sans', sans-serif !important;
    letter-spacing: 0.04em !important;
    transition: all 0.2s !important;
}}

.stButton > button:hover {{
    background: {"#dcb87d" if light_mode else "#e0be82"} !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(201,169,110,{ "0.15" if light_mode else "0.25" }) !important;
}}

[data-testid="stDownloadButton"] > button {{
    background: transparent !important;
    color: {gold} !important;
    border: 1px solid {gold} !important;
    font-weight: 600 !important;
}}

[data-testid="stDownloadButton"] > button:hover {{
    background: rgba(201,169,110,0.1) !important;
}}

.stSpinner > div {{ border-top-color: {gold} !important; }}

label, .stSelectbox label {{ color: {text_sub} !important; font-size: 0.82rem !important; }}

.stSlider .stSlider {{ accent-color: {gold}; }}
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR CONTINUED ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Configuração</div>', unsafe_allow_html=True)

    openrouter_key = st.text_input(
        "OpenRouter API Key",
        value="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",
        type="password",
        placeholder="sk-or-...",
        help="Obtenha em openrouter.ai"
    )
    if not openrouter_key:
        st.warning("⚠️ Insira uma API Key do OpenRouter para funcionar.")

    model_options = {
        "GLM-4.5-Air (gratuito)": "z-ai/glm-4.5-air:free",
        "Mistral 7B (gratuito)": "mistralai/mistral-7b-instruct:free",
        "Llama 3 8B (gratuito)": "meta-llama/llama-3-8b-instruct:free",
        "Llama 3 70B": "meta-llama/llama-3-70b-instruct",
        "GPT-4o Mini": "openai/gpt-4o-mini",
        "Claude 3 Haiku": "anthropic/claude-3-haiku",
        "Gemini Flash 1.5": "google/gemini-flash-1.5",
    }
    selected_model_label = st.selectbox("Modelo IA", list(model_options.keys()))
    selected_model = model_options[selected_model_label]

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Proposta</div>', unsafe_allow_html=True)

    proposal_type = st.selectbox("Tipo de Proposta", [
        "Serviços de Desenvolvimento de Software",
        "Consultoria em Dados / BI",
        "Automação de Processos",
        "Marketing Digital",
        "Design & Branding",
        "Outro (personalizado)"
    ])

    tone = st.selectbox("Tom da Proposta", [
        "Profissional e Formal",
        "Consultivo e Estratégico",
        "Direto e Objetivo",
        "Inovador e Criativo",
    ])

    num_results = st.slider("Referências da web", 3, 10, 5)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Sobre você</div>', unsafe_allow_html=True)
    your_name     = st.text_input("Nome / Empresa", placeholder="Ex: Paulo Silva")
    your_role     = st.text_input("Cargo / Especialidade", placeholder="Ex: Desenvolvedor Full-Stack")

# ─── MAIN ──────────────────────────────────────────────────────────────────────
st.markdown('<h1 class="hero-title"><em>Brief</em>r</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-sub">Pesquisa inteligente → Proposta profissional → PDF pronto</p>', unsafe_allow_html=True)
st.markdown('<hr class="divider">', unsafe_allow_html=True)

col_left, col_right = st.columns([1.1, 1], gap="large")

with col_left:
    st.markdown('<div class="section-label">Briefing do Projeto</div>', unsafe_allow_html=True)

    client_name = st.text_input("Nome do Cliente / Empresa", placeholder="Ex: Imobiliária Silva Lda.")
    project_title = st.text_input("Título do Projeto", placeholder="Ex: Sistema de Automatização de Atendimento WhatsApp")
    project_desc = st.text_area(
        "Descreva o projeto e necessidades do cliente",
        height=180,
        placeholder="Descreva o problema, o que o cliente precisa, contexto do setor, requisitos principais..."
    )
    keywords = st.text_input(
        "Palavras-chave para pesquisa (separadas por vírgula)",
        placeholder="Ex: automação whatsapp, chatbot imobiliário, IA atendimento"
    )

    run_btn = st.button("✦ Gerar Proposta", use_container_width=True)
    
    if st.button("↺ Limpar Briefing", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with col_right:
    tab_result, tab_history = st.tabs(["✨ Resultado Atual", "📁 Histórico"])
    
    with tab_result:
        st.markdown('<div class="section-label">Resultado</div>', unsafe_allow_html=True)
        result_placeholder = st.empty()
        result_placeholder.markdown(
            '<div class="card" style="color:#6b6b78;font-size:0.88rem;text-align:center;padding:3rem 1rem;">'
            '✦<br><br>Preencha o briefing e clique em<br><strong style="color:#c9a96e">Gerar Proposta</strong>'
            '</div>',
            unsafe_allow_html=True
        )

    with tab_history:
        st.markdown('<div class="section-label">Propostas Salvas</div>', unsafe_allow_html=True)
        saved_proposals = load_proposals()
        if not saved_proposals:
            st.info("Nenhuma proposta salva ainda.")
        else:
            for i, p in enumerate(saved_proposals):
                with st.expander(f"📅 {p['date']} - {p['client']} - {p['title']}"):
                    st.markdown(f"**Tipo:** {p['type']}")
                    st.markdown(f"**Palavras-chave:** {p['keywords']}")
                    st.markdown(f'<div class="proposal-box" style="font-size:0.85rem; max-height:300px; overflow-y:auto;">{p["content"]}</div>', unsafe_allow_html=True)
                    
                    # Re-generate PDF functionality
                    try:
                        pdf_data_hist = generate_pdf(
                            proposal_text=p["content"],
                            references=p.get("references", []),
                            project_title=p["title"],
                            client_name=p["client"],
                            your_name=p["your_name"],
                            your_role=p["your_role"]
                        )
                        st.download_button(
                            f"⬇ Baixar PDF Novamente (#{i})",
                            data=pdf_data_hist,
                            file_name=f"re_proposta_{i}.pdf",
                            mime="application/pdf",
                            key=f"dl_{i}"
                        )
                    except Exception as e:
                        st.error(f"Erro ao gerar PDF do histórico: {e}")

# ─── SEARCH FUNCTION ───────────────────────────────────────────────────────────
def search_web(query: str, max_results: int = 5) -> list[dict]:
    results = []
    try:
        with DDGS() as ddgs:
            ddgs_gen = ddgs.text(query, region='pt-pt', safesearch='off', timelimit='m') # 'm' for month
            for i, r in enumerate(ddgs_gen):
                if i >= max_results: break
                results.append({
                    "title": r.get("title", ""),
                    "url":   r.get("href", ""),
                    "body":  r.get("body", "")[:400],
                })
    except Exception as e:
        st.warning(f"Aviso na busca: {e}")
    return results

# ─── OPENROUTER CALL ───────────────────────────────────────────────────────────
def call_openrouter(api_key: str, model: str, system: str, user: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://briefr.app",
        "X-Title": "Briefr",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "temperature": 0.7,
        "max_tokens": 4000,
    }
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=90
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]

# ─── PDF GENERATOR ─────────────────────────────────────────────────────────────
def generate_pdf(
    proposal_text: str,
    references: list[dict],
    project_title: str,
    client_name: str,
    your_name: str,
    your_role: str,
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=2.5*cm,
        bottomMargin=2.5*cm,
        leftMargin=2.8*cm,
        rightMargin=2.8*cm,
    )

    GOLD    = colors.HexColor("#c9a96e")
    DARK    = colors.HexColor("#0d0d0f")
    LIGHT   = colors.HexColor("#e8e3d8")
    MUTED   = colors.HexColor("#9b9aa6")
    BG_CARD = colors.HexColor("#111114")

    styles  = getSampleStyleSheet()

    s_title = ParagraphStyle("s_title",
        fontName="Helvetica-Bold", fontSize=22,
        leading=28, textColor=LIGHT, spaceAfter=4,
        alignment=TA_LEFT)

    s_subtitle = ParagraphStyle("s_subtitle",
        fontName="Helvetica", fontSize=11,
        leading=16, textColor=DARK, spaceAfter=20, # Changed MUTED to DARK
        alignment=TA_LEFT)

    s_label = ParagraphStyle("s_label",
        fontName="Helvetica-Bold", fontSize=7,
        leading=12, textColor=GOLD, spaceBefore=14, spaceAfter=6,
        alignment=TA_LEFT, wordWrap='LTR',
        textTransform='uppercase', charSpace=2)

    s_h2 = ParagraphStyle("s_h2",
        fontName="Helvetica-Bold", fontSize=13,
        leading=18, textColor=DARK, spaceBefore=16, spaceAfter=6) # Changed LIGHT to DARK

    s_body = ParagraphStyle("s_body",
        fontName="Helvetica", fontSize=10,
        leading=17, textColor=DARK, spaceAfter=8, # Changed LIGHT to DARK
        alignment=TA_JUSTIFY)

    s_ref_title = ParagraphStyle("s_ref_title",
        fontName="Helvetica-Bold", fontSize=9,
        leading=13, textColor=LIGHT, spaceAfter=2)

    s_ref_url = ParagraphStyle("s_ref_url",
        fontName="Helvetica-Oblique", fontSize=7.5,
        leading=11, textColor=GOLD, spaceAfter=2)

    s_ref_body = ParagraphStyle("s_ref_body",
        fontName="Helvetica", fontSize=8.5,
        leading=13, textColor=MUTED, spaceAfter=4)

    s_footer = ParagraphStyle("s_footer",
        fontName="Helvetica", fontSize=8,
        leading=12, textColor=DARK, alignment=TA_CENTER) # Changed MUTED to DARK

    story = []

    # ── Header table (gold accent bar + title)
    header_data = [[
        Paragraph(project_title or "Proposta Comercial", s_title),
    ]]
    header_table = Table(header_data, colWidths=[15.4*cm])
    header_table.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0), (-1,-1), 16),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING",   (0,0), (-1,-1), 14),
        ("BOTTOMPADDING",(0,0), (-1,-1), 14),
        ("BACKGROUND",   (0,0), (-1,-1), BG_CARD),
        ("LINEAFTER",    (0,0), (0,0), 4, GOLD),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3*cm))

    # Meta info table
    today   = datetime.now().strftime("%d/%m/%Y")
    meta    = [
        ["Cliente", client_name or "—"],
        ["Elaborado por", f"{your_name or 'Briefr'}  ·  {your_role or ''}"],
        ["Data", today],
    ]
    meta_t = Table(meta, colWidths=[4*cm, 11.4*cm])
    meta_t.setStyle(TableStyle([
        ("FONT",        (0,0), (0,-1), "Helvetica-Bold", 8),
        ("FONT",        (1,0), (1,-1), "Helvetica", 9),
        ("TEXTCOLOR",   (0,0), (0,-1), GOLD),
        ("TEXTCOLOR",   (1,0), (1,-1), DARK), # Changed LIGHT to DARK
        ("TOPPADDING",  (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LINEBELOW",   (0,-1), (-1,-1), 0.5, colors.HexColor("#1e1e24")),
    ]))
    story.append(meta_t)
    story.append(Spacer(1, 0.6*cm))

    # ── Proposal body
    story.append(Paragraph("PROPOSTA", s_label))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#1e1e24"), spaceAfter=10))

    # Parse proposal sections (lines starting with ## or # become headings)
    for line in proposal_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 0.2*cm))
        elif stripped.startswith("## "):
            story.append(Paragraph(stripped[3:], s_h2))
        elif stripped.startswith("# "):
            story.append(Paragraph(stripped[2:], s_h2))
        elif stripped.startswith("- ") or stripped.startswith("• "):
            story.append(Paragraph(f"&bull; {stripped[2:]}", s_body))
        else:
            story.append(Paragraph(stripped, s_body))

    # ── References
    if references:
        story.append(Spacer(1, 0.6*cm))
        story.append(Paragraph("REFERÊNCIAS CONSULTADAS", s_label))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#1e1e24"), spaceAfter=10))

        for i, ref in enumerate(references, 1):
            ref_block = []
            ref_block.append(Paragraph(f"{i}. {ref.get('title','Sem título')}", s_ref_title))
            if ref.get("url"):
                ref_block.append(Paragraph(ref["url"], s_ref_url))
            if ref.get("body"):
                ref_block.append(Paragraph(ref["body"][:300] + "...", s_ref_body))

            ref_data = [[ref_block]]
            ref_table = Table(ref_data, colWidths=[15.4*cm])
            ref_table.setStyle(TableStyle([
                ("LEFTPADDING",  (0,0), (-1,-1), 12),
                ("RIGHTPADDING", (0,0), (-1,-1), 8),
                ("TOPPADDING",   (0,0), (-1,-1), 8),
                ("BOTTOMPADDING",(0,0), (-1,-1), 8),
                ("BACKGROUND",   (0,0), (-1,-1), BG_CARD),
                ("LINEAFTER",    (0,0), (0,0), 3, GOLD),
            ]))
            story.append(KeepTogether(ref_table))
            story.append(Spacer(1, 0.25*cm))

    # ── Footer
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#1e1e24")))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"Proposta gerada em {today} por Briefr  ·  Documento confidencial",
        s_footer
    ))

    doc.build(story)
    return buf.getvalue()

# ─── MAIN LOGIC ────────────────────────────────────────────────────────────────
if run_btn:
    # Validations
    if not openrouter_key:
        st.error("⚠️ Insira a sua OpenRouter API Key na barra lateral.")
        st.stop()
    if not project_desc:
        st.error("⚠️ Descreva o projeto antes de gerar a proposta.")
        st.stop()

    with result_placeholder.container():
        # ── Step 0: Retrieval (Learning)
        historical_context = get_relevant_context(f"{project_title} {project_desc} {keywords}")
        
        # ── Step 1: Search
        st.markdown('<div class="section-label">① Buscando referências...</div>', unsafe_allow_html=True)
        search_query = keywords if keywords else f"{proposal_type} {project_desc[:120]}"

        with st.spinner("Pesquisando na web..."):
            refs = search_web(search_query, num_results)

        if refs:
            st.markdown(f'<span class="status-pill pill-ok">✓ {len(refs)} referências encontradas</span>', unsafe_allow_html=True)
            st.markdown('<div style="height:0.6rem"></div>', unsafe_allow_html=True)
            for r in refs:
                st.markdown(
                    f'<div class="ref-card">'
                    f'<p class="ref-title">{r["title"]}</p>'
                    f'<p class="ref-url">{r["url"]}</p>'
                    f'<p class="ref-body">{r["body"][:220]}{"..." if len(r["body"])>220 else ""}</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown('<span class="status-pill pill-warn">⚠ Nenhuma referência encontrada</span>', unsafe_allow_html=True)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # ── Step 2: Generate proposal
        st.markdown('<div class="section-label">② Gerando proposta com IA...</div>', unsafe_allow_html=True)

        refs_text = "\n".join([
            f"- {r['title']}: {r['body'][:200]}" for r in refs
        ]) if refs else "Nenhuma referência disponível."

        system_prompt = f"""És um consultor sénior com 15 anos de experiência a fechar contratos de alto valor para empresas tecnológicas e de serviços. A tua especialidade é transformar briefings vagos em propostas comerciais que o cliente sente que foram escritas exclusivamente para ele — porque foram.

IDENTIDADE DO AUTOR
Nome: {your_name or 'Consultor'}
Cargo: {your_role or 'Especialista'}
Tipo de serviço: {proposal_type}
Tom: {tone}

FILOSOFIA DE ESCRITA
Cada proposta que escreves segue uma lógica emocional e racional em simultâneo:
1. Começas por espelhar a dor real do cliente — não o que ele pediu, mas o problema por trás do pedido
2. Elevas a conversa: mostras o custo de NÃO agir (tempo perdido, oportunidades falhadas, concorrência a avançar)
3. Apresentas a solução como a consequência natural e inevitável do diagnóstico
4. Usas linguagem concreta: números, prazos, entregáveis tangíveis — nunca promessas vagas
5. Terminas com urgência genuína e um próximo passo claro e de baixo risco

ESTRUTURA OBRIGATÓRIA (usa markdown: # título, ## subtítulo, - lista)

# [Título da proposta — específico, não genérico]

## Contexto e Diagnóstico
Mostra que entendeste o negócio do cliente profundamente. Identifica o problema real (não o sintoma). Usa dados das referências pesquisadas se forem relevantes. 2-3 parágrafos densos.

## O Custo da Inação
Um parágrafo curto e direto: o que acontece se o cliente não resolver isto agora? Perda de tempo, receita, posição competitiva. Sem dramatismo — só factos e lógica.

## A Solução Proposta
Descreve a solução com especificidade técnica e estratégica. Não listes tecnologias — explica o que cada componente resolve para o cliente. Faz a ligação direta entre cada elemento da solução e uma dor identificada no diagnóstico.

## Como Vamos Trabalhar — Fases
Apresenta 3-4 fases com nomes descritivos (não "Fase 1, Fase 2"). Cada fase tem: objetivo, duração estimada, o que o cliente recebe no final.

## O Que Entregas
Lista clara e tangível de entregáveis. Sê específico: não "dashboard", mas "dashboard interativo com X métricas, atualização automática, acesso via browser".

## Resultados Esperados
3-5 benefícios concretos e mensuráveis. Usa linguagem do tipo "redução de X horas semanais", "resposta automática em menos de Y segundos", "visibilidade em tempo real sobre Z". Se tiveres dados das referências, usa-os para calibrar.

## Investimento
Apresenta o investimento como um retorno, não um custo. Sugere estrutura (ex: valor de setup + mensalidade, ou valor total por fases). Inclui o que está incluído e o que não está. Sem valor fixo — usa intervalos ou "a partir de".

## Próximos Passos
Um único parágrafo. Propõe uma reunião de alinhamento de 30 minutos, sem compromisso, para validar detalhes. Cria urgência real (disponibilidade limitada, início de novo ciclo, etc). Termina com uma frase que convida à ação sem pressionar.

REGRAS DE ESCRITA
- Escreve em português europeu correto (não brasileiro)
- Nunca uses frases genéricas como "solução inovadora", "estado da arte", "equipa dedicada"
- Cada parágrafo tem de acrescentar informação nova — nada de repetição
- Se as referências contiverem dados relevantes (tendências, benchmarks, tecnologias), integra-os naturalmente no texto
- Extensão ideal: 600-900 palavras de conteúdo real (sem contar cabeçalhos)
- Tom {tone}: aplica isso na escolha de palavras, não na estrutura"""

        user_prompt = f"""{historical_context}

BRIEFING DO PROJETO

Cliente: {client_name or 'Cliente'}
Título do projeto: {project_title or 'Projeto'}

Descrição e necessidades:
{project_desc}

REFERÊNCIAS PESQUISADAS NA WEB (usa-as para embasar o diagnóstico e os resultados esperados):
{refs_text}

Agora escreve a proposta completa seguindo exactamente a estrutura e filosofia definidas. Começa directamente com o título — sem introduções nem avisos."""

        with st.spinner(f"Gerando proposta com {selected_model_label}..."):
            try:
                proposal = call_openrouter(openrouter_key, selected_model, system_prompt, user_prompt)
                st.markdown('<span class="status-pill pill-ok">✓ Proposta gerada</span>', unsafe_allow_html=True)
                st.markdown('<div style="height:0.6rem"></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="proposal-box">{proposal}</div>', unsafe_allow_html=True)

                # ── Step 3: PDF
                st.markdown('<hr class="divider">', unsafe_allow_html=True)
                st.markdown('<div class="section-label">③ Exportar PDF</div>', unsafe_allow_html=True)

                with st.spinner("Gerando PDF..."):
                    pdf_bytes = generate_pdf(
                        proposal_text=proposal,
                        references=refs,
                        project_title=project_title,
                        client_name=client_name,
                        your_name=your_name,
                        your_role=your_role,
                    )

                filename = f"proposta_{(project_title or 'projeto').lower().replace(' ','_')[:30]}_{datetime.now().strftime('%Y%m%d')}.pdf"

                st.download_button(
                    label="⬇ Baixar Proposta em PDF",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True,
                )
                st.markdown('<span class="status-pill pill-info">PDF pronto para download</span>', unsafe_allow_html=True)

                # ── Step 4: Save (Persistence)
                save_proposal({
                    "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "client": client_name,
                    "title": project_title,
                    "desc": project_desc,
                    "keywords": keywords,
                    "type": proposal_type,
                    "content": proposal,
                    "references": refs,
                    "your_name": your_name,
                    "your_role": your_role
                })
                st.markdown('<span class="status-pill pill-info">✓ Proposta salva no histórico</span>', unsafe_allow_html=True)

            except requests.exceptions.HTTPError as e:
                msg = e.response.text
                if "User not found" in msg or e.response.status_code == 401:
                    st.error("🔑 Erro de Autenticação: A API Key do OpenRouter é inválida ou foi desativada. Verifique se há saldo na sua conta em openrouter.ai.")
                else:
                    st.error(f"Erro na API OpenRouter: {e.response.status_code} — {msg[:300]}")
            except Exception as e:
                st.error(f"Erro inesperado: {e}")
