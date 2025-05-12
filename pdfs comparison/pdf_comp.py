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
    """Return True if any page of the PDF has an extractable text layer."""
    try:
        reader = PdfReader(path)
        for page in reader.pages:
            txt = (page.extract_text() or "").strip()
            if txt:
                return True
        return False
    except Exception:
        return False


def ocr_pdf_to_txt(pdf_path: str) -> str:
    """OCR every page → write to a .txt file → return its path."""
    pages = convert_from_path(pdf_path, dpi=300)
    ocr_chunks: List[str] = []
    for i, img in enumerate(pages, 1):
        text = pytesseract.image_to_string(img, lang="eng")
        ocr_chunks.append(f"\n\n# Page {i}\n{text.strip()}")
    txt_path = tempfile.mktemp(suffix=".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(ocr_chunks))
    return txt_path


openai.api_key = (
    st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
)
if not openai.api_key:
    st.error("OPENAI_API_KEY not set in secrets/environment.")
    st.stop()

st.title("📄🔍 PDF Comparator Chat (native + scans)")

with st.expander("Upload up to two PDFs", expanded=True):
    pdf1 = st.file_uploader("First PDF", type="pdf", key="pdf1")
    pdf2 = st.file_uploader("Second PDF", type="pdf", key="pdf2")

question = st.text_input("Your question (you can ask follow‑ups after the first run)")
ask_btn = st.button("Ask")

if "assistant_id" not in st.session_state:
    st.session_state.assistant_id = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "files_attached" not in st.session_state:
    st.session_state.files_attached = False


def process_upload(file) -> List[str]:

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(file.read())
    tmp.flush()
    tmp_path = tmp.name

    original_file = openai.files.create(file=open(tmp_path, "rb"), purpose="assistants")
    file_ids = [original_file.id]

    if not pdf_has_text(tmp_path):
        txt_path = ocr_pdf_to_txt(tmp_path)
        ocr_file = openai.files.create(file=open(txt_path, "rb"), purpose="assistants")
        file_ids.append(ocr_file.id)
    return file_ids


def ensure_assistant():
    if st.session_state.assistant_id:
        return
    assistant = openai.beta.assistants.create(
        name="PDF Comparator",
        instructions="You are an expert in analysing and comparing PDF documents (including scanned certificates via OCR).",
        model="gpt-4o",  
        tools=[{"type": "file_search"}],
    )
    st.session_state.assistant_id = assistant.id


def ensure_thread():
    if st.session_state.thread_id:
        return
    thread = openai.beta.threads.create()
    st.session_state.thread_id = thread.id



if ask_btn and question:
    ensure_assistant()
    ensure_thread()

    attachments = []
    if not st.session_state.files_attached and pdf1 and pdf2:
        for f in (pdf1, pdf2):
            if f: 
                for fid in process_upload(f):
                    attachments.append({"file_id": fid, "tools": [{"type": "file_search"}]})
        st.session_state.files_attached = True

    msg_kwargs = dict(thread_id=st.session_state.thread_id, role="user", content=question)
    if attachments:
        msg_kwargs["attachments"] = attachments
    openai.beta.threads.messages.create(**msg_kwargs)

    run = openai.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=st.session_state.assistant_id,
    )

    with st.spinner("💬  GPT‑4o is thinking …"):
        while True:
            run_stat = openai.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread_id, run_id=run.id
            )
            if run_stat.status == "completed":
                break
            if run_stat.status == "failed":
                st.error("Assistant failed. Try again.")
                st.stop()
            time.sleep(1)

    msgs = openai.beta.threads.messages.list(thread_id=st.session_state.thread_id).data
    assistant_reply = next(m for m in msgs if m.role == "assistant")
    st.chat_message("assistant").write(assistant_reply.content[0].text.value)

if st.session_state.thread_id:
    st.divider()
    st.subheader("Conversation so far")
    hist = openai.beta.threads.messages.list(thread_id=st.session_state.thread_id).data
    for m in reversed(hist):
        role = "assistant" if m.role == "assistant" else "user"
        st.chat_message(role).write(m.content[0].text.value)
