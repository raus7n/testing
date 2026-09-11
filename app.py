import os
import sqlite3
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from google import genai

load_dotenv()

ROOT = Path(__file__).parent
DB = ROOT / "data" / "knowledge.db"
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

st.set_page_config(page_title="BITS Guide", page_icon="🎓", layout="wide")

CSS = """
<style>
.main .block-container {max-width: 1100px; padding-top: 2rem;}
.hero {padding: 1.5rem 1.7rem; border:1px solid #e5e7eb; border-radius:18px; background:linear-gradient(135deg,#f8fafc,#eef2ff); margin-bottom:1.2rem;}
.hero h1 {margin:0 0 .35rem 0; font-size:2.2rem;}
.hero p {margin:0; color:#475569;}
.source {border-left:4px solid #6366f1; padding:.65rem .8rem; margin:.5rem 0; background:#f8fafc; border-radius:8px; font-size:.9rem;}
.small {color:#64748b; font-size:.85rem;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>🎓 BITS Guide</h1><p>Document-grounded admissions, programmes, placements and financing assistant.</p></div>', unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

if not DB.exists():
    st.error("Knowledge base not found. Run `python ingest.py` first.")
    st.stop()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.warning("Add GEMINI_API_KEY to `.env` before asking questions.")
    st.stop()

client = genai.Client(api_key=api_key)

@st.cache_resource
def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

conn = get_conn()


def retrieve(query: str, k: int = 8):
    # FTS5 lexical retrieval. This is deliberately local and auditable.
    terms = [t for t in query.replace('"',' ').split() if len(t) > 2]
    if not terms:
        return []
    match = " OR ".join(terms[:20])
    try:
        rows = conn.execute("""
            SELECT c.source, c.page, c.chunk, c.text, bm25(chunks_fts) AS score
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.rowid
            WHERE chunks_fts MATCH ?
            ORDER BY score
            LIMIT ?
        """, (match, k)).fetchall()
        return rows
    except sqlite3.Error:
        return []


def answer(query: str, history):
    rows = retrieve(query)
    if not rows:
        return ("I couldn't find enough support for that question in the documents currently loaded. "
                "Please provide the relevant document or a more specific question.", [])

    context_parts = []
    for i, (source, page, chunk, text, score) in enumerate(rows, 1):
        loc = f"{source}, page {page}" if page else source
        context_parts.append(f"SOURCE {i}: {loc}\n{text}")
    context = "\n\n---\n\n".join(context_parts)

    system = """
You are BITS Guide, a document-grounded academic/admissions assistant.

Rules:
1. Use the supplied source excerpts as the primary evidence. Do not invent facts.
2. If the excerpts do not establish a claim, say that the documents do not establish it.
3. Give direct, useful, constructive answers. Do not be dismissive.
4. When requirements differ by programme/campus/university, explicitly distinguish them.
5. Preserve numbers, dates, thresholds, conditions and qualifiers exactly as supported.
6. For placement data, distinguish CTC, TC, offers and averages/medians when relevant.
7. Do not turn estimates or examples into guarantees.
8. End with a compact “Sources” section using [S1], [S2], etc. only for sources actually used.
"""

    history_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history[-6:])
    prompt = f"""{system}

Conversation history:
{history_text}

Retrieved evidence:
{context}

User question:
{query}

Answer using the evidence above. Be concise but sufficiently explanatory.
"""
    resp = client.models.generate_content(model=MODEL, contents=prompt)
    return resp.text, rows

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

q = st.chat_input("Ask about BITS admissions, 2+2 programmes, fees, placements, eligibility…")
if q:
    st.session_state.messages.append({"role":"user", "content":q})
    with st.chat_message("user"):
        st.markdown(q)
    with st.chat_message("assistant"):
        with st.spinner("Searching the document set…"):
            text, rows = answer(q, st.session_state.messages)
        st.markdown(text)
        if rows:
            with st.expander("Evidence used"):
                seen = set()
                for i, (source, page, chunk, txt, score) in enumerate(rows, 1):
                    key = (source, page)
                    if key in seen:
                        continue
                    seen.add(key)
                    loc = f"{source} — page {page}" if page else source
                    st.markdown(f'<div class="source"><b>[S{i}] {loc}</b><br>{txt[:700]}...</div>', unsafe_allow_html=True)
    st.session_state.messages.append({"role":"assistant", "content":text})
