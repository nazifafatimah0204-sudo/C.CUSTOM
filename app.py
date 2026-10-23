"""AI Customs Documentation & Compliance Checker - Streamlit app (run this file)."""
import os
import threading
import time

import streamlit as st

from config import MODELS  # keep this import first: it switches off CrewAI telemetry
from crew_runner import AGENT_MODULES, run_analysis
from n8n_integration import send_to_n8n
from rag import KnowledgeBase
from run_state import RunState
from samples import SAMPLE_DOCS

st.set_page_config(page_title="AI Customs Compliance Checker", page_icon="🛃", layout="wide")

CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1200px;}
.hero {padding: 2rem 2.2rem; border-radius: 22px; color: #fff; margin-bottom: 1.4rem;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 45%, #06b6d4 100%);
  box-shadow: 0 12px 40px rgba(79,70,229,.30);}
.hero h1 {margin: 0 0 .4rem 0; font-size: 2.1rem; font-weight: 800; color: #fff;}
.hero p {margin: 0; font-size: 1.05rem; opacity: .92; color: #fff;}
.pills span {display: inline-block; margin: .9rem .5rem 0 0; padding: .28rem .8rem; border-radius: 999px;
  background: rgba(255,255,255,.18); font-size: .82rem; font-weight: 600; color: #fff;}
.step-title {font-size: 1.15rem; font-weight: 700; margin: 1.4rem 0 .6rem 0;}
.pipeline {display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: .4rem 0 1rem 0;}
.agent-card {border: 1px solid rgba(128,128,128,.30); border-radius: 18px; padding: 16px 16px 14px 16px;
  background: rgba(128,128,128,.07);}
.agent-card .icon {font-size: 1.9rem;}
.agent-card .name {font-weight: 700; margin-top: .3rem;}
.agent-card .desc {font-size: .8rem; opacity: .75; margin: .2rem 0 .7rem 0; min-height: 2.3em;}
.chip {display: inline-block; padding: .2rem .65rem; border-radius: 999px; font-size: .75rem; font-weight: 700;}
.waiting .chip {background: rgba(128,128,128,.20);}
.working {border-color: #7c5cff; box-shadow: 0 0 0 3px rgba(124,92,255,.28), 0 10px 32px rgba(124,92,255,.28);
  animation: pulse 1.5s ease-in-out infinite;}
.working .chip {background: #7c5cff; color: #fff;}
.done {border-color: #22c55e;}
.done .chip {background: rgba(34,197,94,.20); color: #22c55e;}
@keyframes pulse {50% {box-shadow: 0 0 0 7px rgba(124,92,255,.12), 0 10px 32px rgba(124,92,255,.35);}}
.banner {border-radius: 14px; padding: .8rem 1.1rem; margin-bottom: .6rem; font-weight: 600;
  background: rgba(124,92,255,.14); border: 1px solid rgba(124,92,255,.45);}
.banner small {font-weight: 400; opacity: .8;}
@media (max-width: 900px) {.pipeline {grid-template-columns: 1fr 1fr;}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------- helpers ----------
def get_secret(name: str) -> str:
    try:
        return str(st.secrets[name])
    except Exception:
        return os.environ.get(name, "")


def read_upload(file) -> str:
    if file.name.lower().endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(file)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    return file.read().decode("utf-8", errors="ignore")


def pipeline_html(snap: dict, running: bool, finished: bool) -> str:
    cards = []
    for i, mod in enumerate(AGENT_MODULES):
        if finished or i in snap["outputs"]:
            cls, chip = "done", "✅ Done"
        elif running and i == snap["current"]:
            cls, chip = "working", "⚡ Working now"
        else:
            cls, chip = "waiting", "⏳ Waiting"
        cards.append(
            f'<div class="agent-card {cls}"><div class="icon">{mod.ICON}</div>'
            f'<div class="name">Agent {i + 1}: {mod.NAME}</div><div class="desc">{mod.DESCRIPTION}</div>'
            f'<span class="chip">{chip}</span></div>'
        )
    return '<div class="pipeline">' + "".join(cards) + "</div>"


def banner_html(snap: dict) -> str:
    i = min(snap["current"], len(AGENT_MODULES) - 1)
    mod = AGENT_MODULES[i]
    return (f'<div class="banner">{mod.ICON} <b>{mod.NAME}</b> is working now '
            f'<small>&nbsp;·&nbsp; {snap["status"]} &nbsp;·&nbsp; {snap["elapsed"]}s elapsed</small></div>')


# ---------- header ----------
st.markdown(
    '<div class="hero"><h1>🛃 AI Customs Documentation &amp; Compliance Checker</h1>'
    "<p>Upload your shipping documents. A team of four AI agents extracts the data, cross-checks every document, "
    "reviews it against customs rules and writes a compliance report.</p>"
    '<div class="pills"><span>CrewAI</span><span>Groq</span><span>RAG</span><span>n8n</span><span>Streamlit</span></div></div>',
    unsafe_allow_html=True,
)

# ---------- sidebar ----------
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Groq API key", value=get_secret("GROQ_API_KEY"), type="password",
                            help="Get a free key at console.groq.com/keys")
    model_id = st.selectbox("Model", MODELS, index=0)
    max_chars = st.slider("Max characters read per document", 800, 6000, 2200, 200,
                          help="Smaller = fewer tokens = fewer rate-limit errors.")
    cooldown = st.slider("Cool-down between agents (seconds)", 0, 90, 45, 5,
                         help="Free Groq plans allow about 8,000 tokens per minute. Set 0 if you use a paid plan.")
    st.divider()
    st.subheader("📚 RAG knowledge base")
    st.caption("A sample rulebook is built in. Add your own rules (TXT or PDF) to extend it.")
    extra_files = st.file_uploader("Extra regulations", type=["txt", "pdf"], accept_multiple_files=True,
                                   key="extra_rules")
    st.divider()
    st.subheader("🔌 n8n automation")
    n8n_url = st.text_input("n8n Webhook URL (optional)", value=get_secret("N8N_WEBHOOK_URL"))

# ---------- step 1: documents ----------
st.markdown('<div class="step-title">① Add your documents</div>', unsafe_allow_html=True)
use_sample = st.toggle("Use the sample documents (contain deliberate mistakes)", value=True)
uploads = st.file_uploader("Or upload invoice, packing list, bill of lading... (PDF or TXT)",
                           type=["pdf", "txt"], accept_multiple_files=True, key="docs_upload")

docs = {}
if uploads:
    for f in uploads:
        base = f.name.rsplit(".", 1)[0]
        name, n = base, 2
        while name in docs:
            name, n = f"{base}_{n}", n + 1
        docs[name] = read_upload(f)
elif use_sample:
    docs = dict(SAMPLE_DOCS)

if docs:
    cols = st.columns(len(docs))
    for col, (name, text) in zip(cols, docs.items()):
        col.metric(name, f"{len(text):,} chars")
    empty = [n for n, t in docs.items() if len(t.strip()) < 20]
    if empty:
        st.warning(f"No readable text in: {', '.join(empty)}. Scanned PDFs need OCR first; try a text PDF or a TXT file.")
    with st.expander("👀 Preview documents"):
        for name, text in docs.items():
            st.markdown(f"**{name}**")
            st.code(text[:1500] or "(empty)", language=None)
else:
    st.info("Turn on the sample documents or upload at least one file to begin.")

# ---------- step 2: run ----------
st.markdown('<div class="step-title">② Run the agent team</div>', unsafe_allow_html=True)
run_clicked = st.button("🚀 Run compliance check", type="primary", disabled=not docs)

banner_box = st.empty()
pipe_box = st.empty()
log_box = st.empty()

result = st.session_state.get("result")
idle_snap = {"current": 0, "outputs": {}, "status": "", "elapsed": 0}
if result and not run_clicked:
    pipe_box.markdown(pipeline_html(result["snap"], False, not result["snap"]["error"]), unsafe_allow_html=True)
elif not run_clicked:
    pipe_box.markdown(pipeline_html(idle_snap, False, False), unsafe_allow_html=True)

if run_clicked:
    if not api_key.strip():
        st.error("Please paste your Groq API key in the sidebar first.")
        st.stop()
    extra_texts = []
    for f in extra_files or []:
        try:
            extra_texts.append(read_upload(f))
        except Exception as e:
            st.warning(f"Could not read {f.name}: {e}")
    kb = KnowledgeBase(open(os.path.join(os.path.dirname(__file__), "regulations.txt"), encoding="utf-8").read(),
                       extra_texts)

    state = RunState(len(AGENT_MODULES))
    worker = threading.Thread(
        target=run_analysis,
        args=(docs, kb, api_key.strip(), model_id, max_chars, cooldown, state),
        daemon=True,
    )
    worker.start()
    st.session_state.pop("result", None)
    while worker.is_alive():
        snap = state.snapshot()
        banner_box.markdown(banner_html(snap), unsafe_allow_html=True)
        pipe_box.markdown(pipeline_html(snap, True, False), unsafe_allow_html=True)
        log_box.code("\n".join(f"{t}  {m}" for t, m in snap["events"][-8:]) or "Starting...", language=None)
        time.sleep(0.8)
    worker.join()
    snap = state.snapshot()
    banner_box.empty()
    log_box.empty()
    pipe_box.markdown(pipeline_html(snap, False, not snap["error"]), unsafe_allow_html=True)
    st.session_state["result"] = {"snap": snap, "docs": list(docs), "model": model_id}
    result = st.session_state["result"]

# ---------- results ----------
if result:
    snap = result["snap"]
    if snap["error"]:
        st.error(snap["error"])
    else:
        st.markdown('<div class="step-title">③ Results</div>', unsafe_allow_html=True)
        risk = snap["risk"]
        if risk:
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Risk score", f"{risk['score']}/100")
            c2.metric("Critical", risk["critical"])
            c3.metric("Major", risk["major"])
            c4.metric("Minor", risk["minor"])
            c5.metric("Time", f"{snap['elapsed']}s")
            st.progress(risk["score"] / 100, text=risk["level"])
        tab_report, tab_agents, tab_log, tab_n8n = st.tabs(["📄 Report", "🤖 Agent outputs", "🛠 Activity log", "🔌 n8n"])
        with tab_report:
            st.markdown(snap["final"])
            st.download_button("⬇️ Download report (.md)", snap["final"], "customs_compliance_report.md", "text/markdown")
        with tab_agents:
            for i, mod in enumerate(AGENT_MODULES):
                with st.expander(f"{mod.ICON} Agent {i + 1}: {mod.NAME}", expanded=False):
                    st.markdown(snap["outputs"].get(i, "_No output_"))
        with tab_log:
            st.code("\n".join(f"{t}  {m}" for t, m in snap["events"]), language=None)
        with tab_n8n:
            if n8n_url.strip():
                if st.button("📤 Send report to n8n"):
                    ok, msg = send_to_n8n(n8n_url.strip(), snap["final"], risk, result["docs"])
                    (st.success if ok else st.error)(msg)
            else:
                st.info("Paste your n8n Webhook URL in the sidebar to send the report to your n8n workflow "
                        "(email, Google Sheets, Slack...).")
