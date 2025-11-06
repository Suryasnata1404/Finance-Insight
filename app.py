# app.py — ultra-small Streamlit UI for your Milestone 3 pipeline
# Run: streamlit run app.py

import streamlit as st
from datetime import datetime, date
from typing import List, Tuple, Optional
import io

# --- import your backend ---
# Expecting you already have these defined in your project:
#   analyze_text(text, user_entities, event_types, conf_threshold=0.5, timeframe=(start_dt,end_dt))

from finance_insight_backend import analyze_text


# Optional: lightweight PDF text reader (TXT works out-of-the-box)
try:
    import PyPDF2
except Exception:
    PyPDF2 = None

st.set_page_config(page_title="Financial Insight Analyzer", layout="wide")
st.title("📄 Financial Insight Analyzer (Milestone 3)")

# --- Input sidebar ---
with st.sidebar:
    st.header("Settings")
    entities: List[str] = st.multiselect(
        "Entities to extract",
        ["market_cap", "EPS", "revenue_growth", "stock_price_trend"],
        default=["market_cap", "EPS", "revenue_growth", "stock_price_trend"],
    )
    events: List[str] = st.multiselect(
        "Events to detect",
        ["IPO", "M&A", "earnings_call", "dividend"],
        default=["IPO", "M&A", "earnings_call", "dividend"],
    )
    conf = st.slider("NER confidence threshold", 0.0, 0.99, 0.50, 0.01)

    use_time = st.checkbox("Filter events by date range", value=False)
    start_dt: Optional[datetime] = None
    end_dt: Optional[datetime] = None
    if use_time:
        c1, c2 = st.columns(2)
        with c1:
            s: date = st.date_input("Start date", value=date(2010,1,1))
        with c2:
            e: date = st.date_input("End date", value=date.today())
        start_dt = datetime.combine(s, datetime.min.time())
        end_dt = datetime.combine(e, datetime.min.time())

st.subheader("Input")
uploaded = st.file_uploader("Upload a PDF or TXT (optional)", type=["pdf", "txt"])
raw_text = st.text_area("Or paste text here", height=160, placeholder="Paste financial text, 10-K snippet, or news…")

def _read_uploaded_text(file) -> str:
    if file is None:
        return ""
    if file.type == "text/plain":
        return file.read().decode("utf-8", errors="ignore")
    if file.type == "application/pdf" and PyPDF2 is not None:
        reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return ""

text = raw_text.strip()
if not text and uploaded is not None:
    text = _read_uploaded_text(uploaded).strip()

analyze_btn = st.button("🚀 Analyze", use_container_width=True)

if analyze_btn:
    if not text:
        st.warning("Please upload a file or paste some text.")
    else:
        with st.spinner("Analyzing…"):
            timeframe: Optional[Tuple[Optional[datetime], Optional[datetime]]] = (start_dt, end_dt) if use_time else None
            result = analyze_text(text, entities, events, conf_threshold=conf, timeframe=timeframe)

        # --- Display ---
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🔎 Entities")
            ents = result.get("entities", {})
            if not any(ents.values()):
                st.info("No entities extracted with current settings.")
            else:
                for name, items in ents.items():
                    st.markdown(f"**{name}**")
                    st.json(items, expanded=False)

        with col2:
            st.subheader("📢 Events")
            evs = result.get("events", {})
            if not any(evs.values()):
                st.info("No events detected.")
            else:
                st.json(evs, expanded=False)

        st.subheader("✅ Verification (Yahoo Finance)")
        ver = result.get("verified", {})
        ticks = ver.get("tickers", [])
        if ticks:
            st.table(ticks)
        else:
            st.caption("No tickers verified in this text.")

        st.success("Done.")
