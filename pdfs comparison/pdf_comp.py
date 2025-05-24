from __future__ import annotations
import streamlit as st
import openai
import os
import tempfile
import time
from typing import List

import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfReader


def pdf_has_text(path: str) -> bool:
    try:
        reader = PdfReader(path)
        return any((page.extract_text() or "").strip() for page in reader.pages)
    except Exception:
        return False


def ocr_pdf_to_txt(pdf_path: str) -> str:
    pages = convert_from_path(pdf_path, dpi=300)
    chunks: List[str] = []
    for i, img in enumerate(pages, 1):
        txt = pytesseract.image_to_string(img, lang="eng")
        chunks.append(f"\n\n# Page {i}\n{txt.strip()}")
    txt_path = tempfile.mktemp(suffix=".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(chunks))
    return txt_path


def vision_query(paths: List[str], user_q: str) -> str:
    content_parts = []
    for p in paths:
        fid = openai.files.create(file=open(p, "rb"), purpose="user_data").id
        content_parts.append({"type": "file", "file_id": fid})
    content_parts.append({"type": "text", "text": user_q})

    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": content_parts}],
    )
    return resp.choices[0].message.content

openai.api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    st.error("OPENAI_API_KEY not set.")
    st.stop()

st.title("📄🔍 Ask across Documents: make a conversation and ask questions related to the uploaded files")

with st.expander("Upload up to two PDFs", expanded=True):
    pdf1 = st.file_uploader("First PDF", type="pdf")
    pdf2 = st.file_uploader("Second PDF", type="pdf")

question = st.text_input("Ask a question (follow‑ups supported when text/OCR path succeeds)")
ask_btn = st.button("Ask")

if "assistant_id" not in st.session_state:
    st.session_state.assistant_id = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "files_attached" not in st.session_state:
    st.session_state.files_attached = False
if "vision_paths" not in st.session_state:
    st.session_state.vision_paths: List[str] = []
if "attachments" not in st.session_state:
    st.session_state.attachments: List[dict] = []
if "any_text_layer" not in st.session_state:
    st.session_state.any_text_layer = False

if "assistant_id" not in st.session_state:
    st.session_state.assistant_id = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "files_attached" not in st.session_state:
    st.session_state.files_attached = False
if "vision_paths" not in st.session_state:
    st.session_state.vision_paths: List[str] = []


def upload_for_assistant(file) -> tuple[List[str], bool]:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(file.read())
    tmp.flush()
    tmp_path = tmp.name

    base = openai.files.create(file=open(tmp_path, "rb"), purpose="assistants")
    ids = [base.id]
    text_layer = pdf_has_text(tmp_path)
    if not text_layer:
        txt_path = ocr_pdf_to_txt(tmp_path)
        txt = openai.files.create(file=open(txt_path, "rb"), purpose="assistants")
        ids.append(txt.id)
    return ids, text_layer


def ensure_assistant():
    if st.session_state.assistant_id:
        return
    a = openai.beta.assistants.create(
        name="Hybrid PDF Assistant",
        instructions="You analyse PDFs (native text or OCR) and answer questions.",
        model="gpt-4o",
        tools=[{"type": "file_search"}],
    )
    st.session_state.assistant_id = a.id

def ensure_thread():
    if st.session_state.thread_id:
        return
    st.session_state.thread_id = openai.beta.threads.create().id

if ask_btn and question:
    uploads = [f for f in (pdf1, pdf2) if f]
    if not uploads:
        st.error("Upload at least one PDF before asking.")
        st.stop()

    if not st.session_state.files_attached:
        st.session_state.vision_paths = []
        any_text_layer = False
        attachments = []
        for f in uploads:
            vp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            vp.write(f.getvalue()); vp.flush()
            st.session_state.vision_paths.append(vp.name)

            ids, has_text = upload_for_assistant(f)
            any_text_layer = any_text_layer or has_text
            for fid in ids:
                attachments.append({"file_id": fid, "tools": [{"type": "file_search"}]})
        st.session_state.files_attached = True
        st.session_state.attachments = attachments
        st.session_state.any_text_layer = any_text_layer

    use_assistant = st.session_state.any_text_layer

    if use_assistant:
        ensure_thread(); ensure_assistant()
        msg_kwargs = dict(
            thread_id=st.session_state.thread_id,
            role="user",
            content=question,
        )
        if st.session_state.attachments:
            msg_kwargs["attachments"] = st.session_state.attachments
            st.session_state.attachments = []
        openai.beta.threads.messages.create(**msg_kwargs)

        run = openai.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id=st.session_state.assistant_id,
        )
        with st.spinner("GPT‑4o (file_search)…"):
            while True:
                st_r = openai.beta.threads.runs.retrieve(
                    thread_id=st.session_state.thread_id,
                    run_id=run.id,
                )
                if st_r.status == "completed":
                    break
                if st_r.status == "failed":
                    st.error("Assistant run failed."); st.stop()
                time.sleep(1)

        msgs = openai.beta.threads.messages.list(thread_id=st.session_state.thread_id).data
        answer = next(m for m in msgs if m.role == "assistant").content[0].text.value

        fallback_phrases = ["didn't provide the details", "no files uploaded", "search results didn't"]
        if any(p in answer.lower() for p in fallback_phrases):
            with st.spinner("No retrieval hits – switching to vision…"):
                answer = vision_query(st.session_state.vision_paths, question)

        st.chat_message("assistant").write(answer)

    else:
        with st.spinner("GPT‑4o vision…"):
            answer = vision_query(st.session_state.vision_paths, question)
        st.chat_message("assistant").write(answer)

if st.session_state.get("thread_id"):
    st.divider(); st.subheader("Assistant conversation so far")
    for m in reversed(openai.beta.threads.messages.list(thread_id=st.session_state.thread_id).data):
        role = "assistant" if m.role == "assistant" else "user"
        st.chat_message(role).write(m.content[0].text.value)
