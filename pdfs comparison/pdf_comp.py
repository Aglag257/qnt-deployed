import streamlit as st
import openai
import os
import tempfile
import time

openai.api_key = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else os.getenv("OPENAI_API_KEY")

st.title("PDF Comparison Chat with GPT-4")

pdf1 = st.file_uploader("Upload the first PDF", type="pdf")
pdf2 = st.file_uploader("Upload the second PDF", type="pdf")

question = st.text_area("Ask a question comparing the two PDFs")

if st.button("Submit") and pdf1 and pdf2 and question:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp1:
        tmp1.write(pdf1.read())
        pdf1_path = tmp1.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp2:
        tmp2.write(pdf2.read())
        pdf2_path = tmp2.name

    file1 = openai.files.create(file=open(pdf1_path, "rb"), purpose="assistants")
    file2 = openai.files.create(file=open(pdf2_path, "rb"), purpose="assistants")

    assistant = openai.beta.assistants.create(
        name="PDF Comparator",
        instructions="You are an expert in comparing two documents. Use the uploaded PDFs to answer user questions, especially comparisons.",
        model="gpt-4-1106-preview",
        tools=[{"type": "file_search"}]
    )

    thread = openai.beta.threads.create()

    openai.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=question,
        file_ids=[file1.id, file2.id]  # Attach files here instead
    )

    run = openai.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )


    with st.spinner("Getting your answer from GPT-4..."):
        while True:
            run_status = openai.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            if run_status.status == "completed":
                break
            elif run_status.status == "failed":
                st.error("The assistant failed to process the request.")
                break
            time.sleep(1)

        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        response = messages.data[0].content[0].text.value
        st.markdown("### Answer")
        st.write(response)

    os.remove(pdf1_path)
    os.remove(pdf2_path)
