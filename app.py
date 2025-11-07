import streamlit as st
from datetime import datetime, date
from typing import List, Tuple, Optional
import io

# --- import your backend ---
from finance_insight_backend import analyze_text

try:
    import PyPDF2
except Exception:
    PyPDF2 = None

# Wide clean dashboard with minimal sidebar
st.set_page_config(page_title="Financial Insight Chat", layout="wide")
st.markdown("""
    <style>
    .stApp {background-color: #f6f8fa;}
    .report-card {background: #fff; border-radius: 18px; box-shadow: 0 2px 12px #eee; padding: 24px 20px; margin-bottom: 24px;}
    .chat-bubble {background: #e8eef6; border-radius: 30px; padding: 10px 12px; margin: 12px 0;}
    .chat-bubble.user {background: #cbe9de;}
    .chat-entity {background: linear-gradient(90deg,#e6ffc0,#eeebff); border-radius: 8px; padding: 4px 12px; display: inline-block; margin-right: 6px;}
    .rounded-btn button {border-radius: 25px!important;}
    </style>
""", unsafe_allow_html=True)
st.title("📄 Financial Insight | Chat With Your Document")

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/000000/bank-building.png", width=55)
    st.markdown("> **Settings**", unsafe_allow_html=True)
    entities: List[str] = st.multiselect(
        "Entities to extract",
        ["market_cap", "EPS", "revenue_growth", "stock_price_trend", "dividend_yield", "pe_ratio"],
        default=["market_cap", "EPS", "revenue_growth"],
    )
    events: List[str] = st.multiselect(
        "Events to detect",
        ["IPO", "M&A", "earnings_call", "dividend"],
        default=["IPO", "M&A", "earnings_call"],
    )
    conf = st.slider("Confidence threshold", 0.0, 0.99, 0.50, 0.01)

    use_time = st.checkbox("Filter events by date", value=False)
    start_dt, end_dt = None, None
    if use_time:
        s = st.date_input("Start", value=date(2022, 1, 1))
        e = st.date_input("End", value=date.today())
        start_dt = datetime.combine(s, datetime.min.time())
        end_dt = datetime.combine(e, datetime.min.time())

st.markdown('<div class="report-card">', unsafe_allow_html=True)
st.subheader("🗂️ Upload Your Financial Report")
uploaded = st.file_uploader("Upload (.pdf, .txt) or paste text below", type=["pdf", "txt"])
raw_text = st.text_area("Paste text here", height=120, placeholder="Paste financial text, a news snippet, or report details…")

def _read_uploaded_text(file) -> str:
    if file is None: return ""
    if file.type == "text/plain": return file.read().decode("utf-8", errors="ignore")
    if file.type == "application/pdf" and PyPDF2 is not None:
        reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return ""

text = raw_text.strip()
if not text and uploaded is not None:
    text = _read_uploaded_text(uploaded).strip()

st.markdown('</div>', unsafe_allow_html=True)

analyze_btn = st.button("💡 Analyze", use_container_width=True)

if analyze_btn:
    if not text:
        st.markdown('<div class="chat-bubble user">⚠️ Please upload or paste some text.</div>', unsafe_allow_html=True)
    else:
        with st.spinner("🔎 Analyzing your document…"):
            timeframe: Optional[Tuple[Optional[datetime], Optional[datetime]]] = (start_dt, end_dt) if use_time else None
            result = analyze_text(text, entities, events, conf_threshold=conf, timeframe=timeframe)

        # --- Chat Display Layout ---
        st.markdown('<div class="report-card">', unsafe_allow_html=True)

        st.markdown('<div class="chat-bubble">✅ <b>Successfully loaded your report.</b></div>', unsafe_allow_html=True)
        st.markdown('<div class="chat-bubble user">💬 <b>Question:</b> What does this report contain?</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="chat-bubble">🧾 <b>Summary:</b> {result.get("summary", "AI summary coming soon…")}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        
        st.subheader("🔎 Extracted Entities")
        ents = result.get("entities", {})
        for name, items in ents.items():
            st.markdown(f"<span class='chat-entity'>{name}</span>", unsafe_allow_html=True)
            if not items:
                st.caption("— none —")
                continue
            for it in items[:10]:
                label = it.get("raw") or it.get("text") or str(it)
                st.write("•", label)


        st.subheader("📢 Detected Events")
        evs = result.get("events", {})
        if not any(evs.values()):
            st.info("No financial events detected.")
        else:
            for name, items in evs.items():
                st.markdown(f"<span class='chat-entity'>{name}</span>", unsafe_allow_html=True)
                st.json(items, expanded=False)

        st.subheader("✅ Verified (Yahoo Finance)")
        ver = result.get("verified", {})
        ticks = ver.get("tickers", [])
        if ticks:
            st.table(ticks)
        else:
            st.caption("No tickers verified in this text.")
        
        st.success("All done!")
        st.markdown('</div>', unsafe_allow_html=True)
