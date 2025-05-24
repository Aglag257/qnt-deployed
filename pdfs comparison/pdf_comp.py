from __future__ import annotations
import streamlit as st
import os
import tempfile
from typing import List
import google.generativeai as genai
from PIL import Image
from pypdf import PdfReader
from pdf2image import convert_from_path


genai.configure(api_key=st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY"))
if not (st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")):
    st.error("GEMINI_API_KEY not set.")
    st.stop()


def pdf_to_images(pdf_path: str) -> List[Image.Image]:
    """Converts PDF pages to PIL Image objects."""
    return convert_from_path(pdf_path, dpi=300)


def vision_query_gemini(image_paths: List[str], user_q: str) -> str:
    model = genai.GenerativeModel('gemini-pro-vision')
    content_parts = []

    for pdf_path in image_paths:
        images = pdf_to_images(pdf_path)
        for i, img in enumerate(images):
            content_parts.append(img)
    
    content_parts.append(user_q)

    try:
        response = model.generate_content(content_parts)
        return response.text
    except Exception as e:
        return f"Error querying Gemini Vision: {e}"


st.title("📄🔍 Ask across Documents: make a conversation and ask questions related to the uploaded files")

with st.expander("Upload up to two PDFs", expanded=True):
    pdf1 = st.file_uploader("First PDF", type="pdf")
    pdf2 = st.file_uploader("Second PDF", type="pdf")

question = st.text_input("Ask a question (follow‑ups supported)")
ask_btn = st.button("Ask")

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history: List[dict] = []
if "uploaded_pdf_paths" not in st.session_state:
    st.session_state.uploaded_pdf_paths: List[str] = []
if "files_processed_for_gemini" not in st.session_state:
    st.session_state.files_processed_for_gemini = False


if ask_btn and question:
    uploads = [f for f in (pdf1, pdf2) if f]
    if not uploads:
        st.error("Upload at least one PDF before asking.")
        st.stop()

    if not st.session_state.files_processed_for_gemini:
        st.session_state.uploaded_pdf_paths = []
        for uploaded_file in uploads:

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp.write(uploaded_file.getvalue())
            tmp.flush()
            st.session_state.uploaded_pdf_paths.append(tmp.name)
        st.session_state.files_processed_for_gemini = True

    st.session_state.conversation_history.append({"role": "user", "content": question})

    with st.spinner("Asking Gemini Vision..."):
        answer = vision_query_gemini(st.session_state.uploaded_pdf_paths, question)
        
        st.session_state.conversation_history.append({"role": "assistant", "content": answer})

    st.chat_message("assistant").write(answer)


if st.session_state.conversation_history:
    st.divider()
    st.subheader("Conversation so far")
    for chat_message in st.session_state.conversation_history:
        role = chat_message["role"]
        content = chat_message["content"]
        st.chat_message(role).write(content)