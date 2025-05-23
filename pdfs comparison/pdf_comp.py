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
    ocr_chunks: List[str] = []
    for i, img in enumerate(pages, 1):
        text = pytesseract.image_to_string(img, lang="eng")
        ocr_chunks.append(f"\n\n# Page {i}\n{text.strip()}")
    txt_path = tempfile.mktemp(suffix=".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(ocr_chunks))
    return txt_path


def vision_query(paths: List[str], user_q: str) -> str:
    file_parts = []
    file_ids = []
    for p in paths:
        fid = openai.files.create(file=open(p, "rb"), purpose="user_data").id
        file_ids.append(fid)
        file_parts.append({"type": "input_file", "file_id": fid})
    messages = [
        {
            "role": "user",
            "content": file_parts + [{"type": "input_text", "text": user_q}],
        }
    ]
    resp = openai.chat.completions.create(model="gpt-4o", messages=messages)
    return resp.choices[0].message.content

openai.api_key = (
    st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
)
if not openai.api_key:
    st.error("OPENAI_API_KEY not set."); st.stop()

st.title("📄🔍 Ask across Documents: make a conversation and ask questions related to the uploaded files")

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


def upload_for_assistant(file) -> tuple[List[str], bool]:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(file.read()); tmp.flush()
    tmp_path = tmp.name

    base_file = openai.files.create(file=open(tmp_path, "rb"), purpose="assistants")
    ids = [base_file.id]
    has_txt = pdf_has_text(tmp_path)
    if not has_txt:
        txt_path = ocr_pdf_to_txt(tmp_path)
        txt_file = openai.files.create(file=open(txt_path, "rb"), purpose="assistants")
        ids.append(txt_file.id)
    return ids, has_txt


def ensure_assistant():
    if st.session_state.assistant_id: return
    a = openai.beta.assistants.create(
        name="Hybrid PDF Assistant",
        instructions="You analyse PDFs (native text or OCR) and answer questions.",
        model="gpt-4o",
        tools=[{"type": "file_search"}],
    )
    st.session_state.assistant_id = a.id

def ensure_thread():
    if st.session_state.thread_id: return
    st.session_state.thread_id = openai.beta.threads.create().id

if ask_btn and question:
    tmp_paths: List[str] = []
    any_text = False

    uploads = [f for f in (pdf1, pdf2) if f]
    if not uploads:
        st.error("Please upload at least one PDF."); st.stop()

    attachments = []
    if not st.session_state.files_attached:
        filenames = []
        for f in uploads:
            filenames.append(f.name)
            ids, has_txt = upload_for_assistant(f)
            any_text = any_text or has_txt
            for fid in ids:
                attachments.append({"file_id": fid, "tools": [{"type": "file_search"}]})
            t = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            t.write(f.getvalue()); t.flush(); tmp_paths.append(t.name)
        st.session_state.files_attached = True
    else:
        ensure_thread(); ensure_assistant()

    if any_text:
        ensure_thread(); ensure_assistant()
        user_hint = "" if not attachments else f"(Refer to uploaded docs by name: {', '.join(f.name for f in uploads)})"
        msg_kwargs = dict(thread_id=st.session_state.thread_id, role="user", content=question + user_hint)
        if attachments:
            msg_kwargs["attachments"] = attachments
        openai.beta.threads.messages.create(**msg_kwargs)
        run = openai.beta.threads.runs.create(thread_id=st.session_state.thread_id, assistant_id=st.session_state.assistant_id)
        with st.spinner("GPT‑4o (file_search) …"):
            while True:
                stat = openai.beta.threads.runs.retrieve(thread_id=st.session_state.thread_id, run_id=run.id)
                if stat.status == "completed": break
                if stat.status == "failed": st.error("Run failed"); st.stop()
                time.sleep(1)
        msgs = openai.beta.threads.messages.list(thread_id=st.session_state.thread_id).data
        reply = next(m for m in msgs if m.role == "assistant").content[0].text.value
        st.chat_message("assistant").write(reply)
    else:
        if "vision_paths" not in st.session_state:
            st.session_state.vision_paths = []
            for f in uploads:
                t = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                t.write(f.getvalue()); t.flush(); st.session_state.vision_paths.append(t.name)
        with st.spinner("GPT‑4o vision …"):
            vision_answer = vision_query(st.session_state.vision_paths, question)
        st.chat_message("assistant").write(vision_answer)

if st.session_state.get("thread_id"):
    st.divider(); st.subheader("File‑search conversation so far")
    for m in reversed(openai.beta.threads.messages.list(thread_id=st.session_state.thread_id).data):
        role = "assistant" if m.role == "assistant" else "user"
        st.chat_message(role).write(m.content[0].text.value)
