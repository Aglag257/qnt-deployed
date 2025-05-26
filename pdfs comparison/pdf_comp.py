from __future__ import annotations
import streamlit as st
import os
import tempfile
from typing import List
import google.generativeai as genai

genai.configure(api_key=st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY"))
if not (st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")):
    st.error("GEMINI_API_KEY not set.")
    st.stop()

def generate_content_with_pdfs(pdf_bytes_list: List[bytes], user_q: str) -> str:
    model = genai.GenerativeModel('gemini-1.5-flash')
    contents = []
    
    for i, pdf_bytes in enumerate(pdf_bytes_list):
        contents.append({
            "mime_type": "application/pdf",
            "data": pdf_bytes
        })
    
    enhanced_prompt = f"""
    You are analyzing scanned PDF documents that may contain tables, forms, or structured data.
    
    Please carefully examine ALL uploaded PDF documents and:
    1. Use OCR to read any text, numbers, or values in the documents
    2. Pay special attention to tables, boxes, fields, and structured layouts
    3. Look for percentages, chemical compositions, test results, or numerical data
    4. If you see boxes or fields with labels, extract both the label and the value
    
    User's specific question: {user_q}
    
    If the documents contain tables or structured data, present the information clearly.
    If you cannot read certain parts due to image quality, please mention that specifically.
    
    For each document, try to identify:
    - Document type (test report, certificate, etc.)
    - Any percentage values (like C%, Cu%, Co%)
    - Numerical data in tables or forms
    - Field labels and their corresponding values
    """
    
    contents.append(enhanced_prompt)
    
    try:
        response = model.generate_content(
            contents,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=2048,
            )
        )
        return response.text
    except Exception as e:
        return f"Error querying Gemini: {e}"

def generate_comparison_prompt(user_question: str) -> str:
    """Generate a more specific prompt for comparing documents"""
    return f"""
    Compare the uploaded PDF documents and answer this question: {user_question}
    
    Instructions:
    - Carefully examine both documents using OCR
    - Look for tables, forms, or structured data
    - Extract specific values requested (percentages, measurements, etc.)
    - Present findings in a clear comparison format
    - If documents are test reports or certificates, identify the document types
    - Mention if any text is unclear due to scan quality
    
    Format your response as:
    Document 1: [findings]
    Document 2: [findings]
    Comparison: [similarities/differences]
    """

st.title("📄🔍 Ask across Documents: make a conversation and ask questions related to the uploaded files")
st.caption("Optimized for scanned documents, test reports, and certificates")

with st.expander("Upload up to two PDFs", expanded=True):
    pdf1 = st.file_uploader("First PDF", type="pdf", help="Upload scanned documents, test reports, or certificates")
    pdf2 = st.file_uploader("Second PDF", type="pdf", help="Optional second document for comparison")

# Example questions for guidance
with st.expander("💡 Example Questions"):
    st.write("""
    - What are the values for C%, Cu%, Co% in these documents?
    - Compare the test results between these two reports
    - Extract all percentage values from the documents
    - What are the material properties listed in these certificates?
    - List all numerical values found in tables or forms
    """)

question = st.text_input(
    "Ask a question about the documents", 
    placeholder="e.g., What are the values in the boxes: C%, Cu%, Co%?",
    help="Ask specific questions about values, percentages, or data in your scanned documents"
)

ask_btn = st.button("🔍 Analyze Documents", type="primary")

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history: List[dict] = []
if "uploaded_pdf_bytes" not in st.session_state:
    st.session_state.uploaded_pdf_bytes: List[bytes] = []
if "files_processed_for_gemini" not in st.session_state:
    st.session_state.files_processed_for_gemini = False

if ask_btn and question:
    uploads = [f for f in (pdf1, pdf2) if f]
    if not uploads:
        st.error("📋 Please upload at least one PDF before asking.")
        st.stop()
    
    if not st.session_state.files_processed_for_gemini:
        st.session_state.uploaded_pdf_bytes = []
        for uploaded_file in uploads:
            st.session_state.uploaded_pdf_bytes.append(uploaded_file.getvalue())
        st.session_state.files_processed_for_gemini = True
        
        st.success(f"✅ Processed {len(uploads)} document(s)")
    
    st.session_state.conversation_history.append({"role": "user", "content": question})
    
    with st.spinner("🔍 Analyzing documents with enhanced OCR..."):
        answer = generate_content_with_pdfs(st.session_state.uploaded_pdf_bytes, question)
        st.session_state.conversation_history.append({"role": "assistant", "content": answer})
    
    st.chat_message("assistant").write(answer)

if st.session_state.conversation_history:
    st.divider()
    st.subheader("📝 Conversation History")
    for chat_message in st.session_state.conversation_history:
        role = chat_message["role"]
        content = chat_message["content"]
        st.chat_message(role).write(content)

if st.button("🔄 Reset Conversation"):
    st.session_state.conversation_history = []
    st.session_state.uploaded_pdf_bytes = []
    st.session_state.files_processed_for_gemini = False
    st.rerun()

