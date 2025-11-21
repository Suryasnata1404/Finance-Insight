# app.py
import streamlit as st
from datetime import datetime, date
from typing import List, Tuple, Optional
import io, json

# --- import your backend functions ---
# make sure finance_insight_backend.py defines analyze_text and analyze_pdf_file
from finance_insight_backend import analyze_text, analyze_pdf_file

try:
    import PyPDF2
except Exception:
    PyPDF2 = None

# UI config + small styles
st.set_page_config(page_title="Financial Insight | Chat With Your Document", layout="wide")
st.markdown(
    """
    <style>
    .stApp {background-color: #f6f8fa;}
    .report-card {background: #fff; border-radius: 12px; box-shadow: 0 2px 10px #eee; padding: 18px; margin-bottom: 18px;}
    .chat-bubble {background: #eef6ff; border-radius: 14px; padding: 10px 12px; margin: 8px 0;}
    .chat-bubble.user {background: #d9f7ea;}
    .chat-entity {background: linear-gradient(90deg,#e6ffc0,#eeebff); border-radius: 8px; padding: 4px 10px; display: inline-block; margin-right: 8px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📄 Financial Insight | Chat With Your Document")

# Sidebar: settings
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/000000/bank-building.png", width=64)
    st.markdown("## Settings")
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

# Upload area
st.markdown('<div class="report-card">', unsafe_allow_html=True)
st.subheader("🗂️ Upload Your Financial Report")
uploaded = st.file_uploader("Upload (.pdf, .txt) or paste text below", type=["pdf", "txt"])
raw_text = st.text_area("Paste text here", height=140, placeholder="Paste financial text, a news snippet, or report details…")
st.markdown('</div>', unsafe_allow_html=True)

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
uploaded_file_obj = uploaded
if not text and uploaded_file_obj is not None:
    # If a PDF uploaded we will use analyze_pdf_file later — still keep a text fallback
    if uploaded_file_obj.type == "text/plain":
        text = _read_uploaded_text(uploaded_file_obj).strip()

analyze_btn = st.button("💡 Analyze", use_container_width=True)

if analyze_btn:
    if not text and uploaded_file_obj is None:
        st.markdown('<div class="chat-bubble user">⚠️ Please upload or paste some text.</div>', unsafe_allow_html=True)
    else:
        with st.spinner("🔎 Analyzing your document…"):
            timeframe: Optional[Tuple[Optional[datetime], Optional[datetime]]] = (start_dt, end_dt) if use_time else None

            # Prefer the richer PDF pipeline when a PDF file is uploaded
            result = {}
            try:
                if uploaded_file_obj is not None and uploaded_file_obj.type == "application/pdf":
                    # analyze_pdf_file expects a path or file-like; pass the upload bytes buffer
                    buf = io.BytesIO(uploaded_file_obj.read())
                    result = analyze_pdf_file(
                        buf,
                        user_entities=entities,
                        event_types=events,
                        conf_threshold=conf,
                        timeframe=timeframe
                    )
                else:
                    # fall back to text-based pipeline
                    result = analyze_text(text, entities, events, conf_threshold=conf, timeframe=timeframe)
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                result = analyze_text(text or "", entities, events, conf_threshold=conf, timeframe=timeframe)

        # --- Top chat-like summary area ---
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        st.markdown('<div class="chat-bubble">✅ <b>Successfully loaded your report.</b></div>', unsafe_allow_html=True)
        st.markdown('<div class="chat-bubble user">💬 <b>Question:</b> What does this report contain?</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="chat-bubble">🧾 <b>Summary:</b> {result.get("summary", "AI summary coming soon…")}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ---- Document segmentation (short) ----
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        st.subheader(" Document Segmentation")
        sections = result.get("sections", {}) or {}
        if not sections:
            st.info("No segmentation available.")
        else:
            # Show short snippet for each detected section inside an expander
            for name, snippet in sections.items():
                if not snippet:
                    continue
                with st.expander(name, expanded=False):
                    # show only short cleaned snippet (first 600 chars) + option to expand full
                    short = snippet.strip().replace("\n", " ")[:600]
                    st.write(short + ("…" if len(snippet) > 600 else ""))
                    if st.button(f"Show full {name}", key=f"full_{name}"):
                        st.write(snippet)
        st.markdown('</div>', unsafe_allow_html=True)

        # ---- Parsed tables ----
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        st.subheader("Parsed Tables (first 6 shown)")
        parsed_tables = result.get("tables") or []
        if not parsed_tables:
            st.info("No parsed tables found.")
        else:
            show_n = min(6, len(parsed_tables))
            for i in range(show_n):
                t = parsed_tables[i]
                st.markdown(f"**Table {i+1} — page {t.get('page', '?')} — type: {t.get('type','Unknown')}**")
                raw_df = t.get("raw")
                numeric_df = t.get("numeric")
                # show raw preview (first 6 rows)
                try:
                    if raw_df is not None:
                        st.markdown("Raw table preview (first 6 rows):")
                        st.dataframe(raw_df.head(6), use_container_width=True)
                except Exception:
                    st.text(str(raw_df)[:1000])

                # show normalized numeric preview
                try:
                    if numeric_df is not None:
                        st.markdown("Normalized numeric preview (first 6 rows):")
                        st.dataframe(numeric_df.head(6), use_container_width=True)
                except Exception:
                    pass

                # small download for each table (JSON)
                try:
                    jt = {
                        "page": t.get("page"),
                        "type": t.get("type"),
                        "raw_head": raw_df.head(6).to_dict(orient="records") if raw_df is not None else None,
                        "numeric_head": numeric_df.head(6).to_dict(orient="records") if numeric_df is not None else None,
                    }
                    st.download_button(f"Download table {i+1} (JSON)", json.dumps(jt, default=str), file_name=f"table_{i+1}_page{t.get('page')}.json")
                except Exception:
                    pass

                st.markdown("---")

            if len(parsed_tables) > show_n:
                st.info(f"{len(parsed_tables)-show_n} more parsed tables not shown. Use download to export all.")

            # global download (all tables)
            try:
                all_tables_export = []
                for t in parsed_tables:
                    raw = t.get("raw")
                    numeric = t.get("numeric")
                    all_tables_export.append({
                        "page": t.get("page"),
                        "type": t.get("type"),
                        "raw_head": raw.head(6).to_dict(orient="records") if raw is not None else None,
                        "numeric_head": numeric.head(6).to_dict(orient="records") if numeric is not None else None,
                    })
                st.download_button("Download all parsed tables (JSON)", json.dumps(all_tables_export, default=str), file_name="parsed_tables.json")
            except Exception:
                pass

        st.markdown('</div>', unsafe_allow_html=True)

        # ---- Extracted Entities ----
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        st.subheader("🔎 Extracted Entities")
        ents = result.get("entities", {}) or {}
        if not ents:
            st.caption("— none —")
        else:
            for name, items in ents.items():
                st.markdown(f"<span class='chat-entity'>{name}</span>", unsafe_allow_html=True)
                if not items:
                    st.caption("— none —")
                else:
                    for it in items[:20]:
                        label = it.get("raw") or it.get("text") or str(it)
                        st.write("•", label)
        # download entities
        try:
            st.download_button("Download extracted entities (JSON)", json.dumps(ents, default=str), file_name="entities.json")
        except Exception:
            pass
        st.markdown('</div>', unsafe_allow_html=True)

        # ---- Events ----
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        st.subheader("📢 Detected Events")
        evs = result.get("events", {}) or {}
        if not evs or not any(evs.values()):
            st.info("No financial events detected.")
        else:
            for name, items in evs.items():
                st.markdown(f"<span class='chat-entity'>{name}</span>", unsafe_allow_html=True)
                if not items:
                    st.caption("— none —")
                else:
                    st.json(items, expanded=False)
        st.markdown('</div>', unsafe_allow_html=True)

        # ---- Verified tickers ----
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        st.subheader("✅ Verified (Yahoo Finance)")
        ver = result.get("verified", {}) or {}
        ticks = ver.get("tickers", []) if isinstance(ver, dict) else []
        if ticks:
            try:
                st.table(ticks)
                st.download_button("Download verified tickers (JSON)", json.dumps(ticks, default=str), file_name="tickers.json")
            except Exception:
                st.write(ticks)
        else:
            st.caption("No tickers verified in this text.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.success("All done!")
