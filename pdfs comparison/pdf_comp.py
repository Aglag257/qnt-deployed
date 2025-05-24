from __future__ import annotations
import streamlit as st
import os
import tempfile
from typing import List
import google.generativeai as genai
from google.generativeai import GenerativeModel
from google.generativeai.types import Part


genai.configure(api_key=st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY"))
if not (st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")):
    st.error("GEMINI_API_KEY not set.")
    st.stop()


def generate_content_with_pdfs(pdf_bytes_list: List[bytes], user_q: str) -> str:
    """Sends a query to Gemini with multiple PDF byte streams."""
    model = GenerativeModel('gemini-1.5-flash')

    contents = []
    for pdf_bytes in pdf_bytes_list:
        contents.append(Part.from_bytes(data=pdf_bytes, mime_type='application/pdf'))
    
    contents.append(user_q)

    try:
        response = model.generate_content(contents)
        return response.text
    except Exception as e:
        return f"Error querying Gemini: {e}"


st.title("📄🔍 Ask across Documents: make a conversation and ask questions related to the uploaded files")

with st.expander("Upload up to two PDFs", expanded=True):
    pdf1 = st.file_uploader("First PDF", type="pdf")
    pdf2 = st.file_uploader("Second PDF", type="pdf")

question = st.text_input("Ask a question (follow‑ups supported)")
ask_btn = st.button("Ask")

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history: List[dict] = []
if "uploaded_pdf_bytes" not in st.session_state:
    st.session_state.uploaded_pdf_bytes: List[bytes] = []
if "files_processed_for_gemini" not in st.session_state:
    st.session_state.files_processed_for_gemini = False


if ask_btn and question:
    uploads = [f for f in (pdf1, pdf2) if f]
    if not uploads:
        st.error("Upload at least one PDF before asking.")
        st.stop()

    if not st.session_state.files_processed_for_gemini:
        st.session_state.uploaded_pdf_bytes = []
        for uploaded_file in uploads:
            st.session_state.uploaded_pdf_bytes.append(uploaded_file.getvalue())
        st.session_state.files_processed_for_gemini = True

    st.session_state.conversation_history.append({"role": "user", "content": question})

    with st.spinner("Asking Gemini..."):
        answer = generate_content_with_pdfs(st.session_state.uploaded_pdf_bytes, question)
        
        st.session_state.conversation_history.append({"role": "assistant", "content": answer})

    st.chat_message("assistant").write(answer)


if st.session_state.conversation_history:
    st.divider()
    st.subheader("Conversation so far")
    for chat_message in st.session_state.conversation_history:
        role = chat_message["role"]
        content = chat_message["content"]
        st.chat_message(role).write(content)