# app.py
import streamlit as st
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI
from dotenv import load_dotenv
import os
import subprocess

load_dotenv()

ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = "docubot-index"
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
CHAT_MODEL = "gpt-4o-mini"

search_client = SearchClient(ENDPOINT, INDEX_NAME, AzureKeyCredential(KEY))
llm = AzureOpenAI(azure_endpoint=OPENAI_ENDPOINT, api_key=OPENAI_KEY, api_version="2024-02-01")

def get_embedding(text):
    return llm.embeddings.create(input=text, model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")).data[0].embedding

def retrieve(query, k=3):
    emb = get_embedding(query)
    results = search_client.search(
        search_text=query,
        vector_queries=[{"kind": "vector", "vector": emb, "fields": "content_vector", "k": k}],
        select=["content", "source"]
    )
    return [(r["content"], r["source"]) for r in results]

def answer_question(question):
    context_docs = retrieve(question)
    context = "\n\n".join(f"Source: {src}\n{ctx}" for ctx, src in context_docs)
    prompt = f"""Use only the following context to answer:

{context}

Question: {question}
Answer:"""

    response = llm.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content

# UI
st.title("DocuBot — AI Document Q&A")
st.write("Upload PDFs → Ask questions")

# —————— SIDEBAR: PDF UPLOAD & INDEXING ——————
# with st.sidebar:
#     st.header("Upload PDFs")
#     uploaded = st.file_uploader(
#         "Drop PDFs here", 
#         type="pdf", 
#         accept_multiple_files=True
#     )

    # —————— SIDEBAR ——————
with st.sidebar:
    st.header("Upload PDFs")
    uploaded = st.file_uploader("Drop PDFs here", type="pdf", accept_multiple_files=True)

    # ← ADD CLEAR BUTTON
    if st.button("🗑️ Clear Index (Remove ALL old data)"):
        with st.spinner("Deleting ALL documents from Azure AI Search..."):
            try:
                while True:
                    results = search_client.search(
                        search_text="*", 
                        top=1000, 
                        select=["id"]
                    )
                    ids = [r["id"] for r in results]
                    if not ids:
                        break
                    search_client.delete_documents([{"id": id} for id in ids])
                st.success("Index FULLY CLEARED. Upload and index new PDFs.")
            except Exception as e:
                st.error(f"Clear failed: {e}")

    elif st.button("Index Documents") and uploaded:
        # 1. FORCE CLEAR OLD INDEX
        with st.spinner("Clearing old index..."):
            try:
                while True:
                    results = search_client.search(
                        search_text="*", 
                        top=1000, 
                        select=["id"]
                    )
                    ids = [r["id"] for r in results]
                    if not ids:
                        break
                    search_client.delete_documents([{"id": id} for id in ids])
                st.success("Old index cleared")
            except Exception as e:
                st.error(f"Clear failed: {e}")

        # 2. SAVE NEW PDFs
        os.makedirs("docs", exist_ok=True)
        for f in uploaded:
            with open(f"docs/{f.name}", "wb") as out:
                out.write(f.getbuffer())
        st.success(f"Saved {len(uploaded)} PDF(s)")

        # 3. RUN INGESTION
        with st.spinner("Indexing new PDFs..."):
            result = subprocess.run(
                ["python", "ingest_pdf.py"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                st.success("New PDFs indexed! Ask questions now.")
                if result.stdout.strip():
                    st.code(result.stdout.strip(), language="text")
            else:
                st.error("Ingestion failed:")
                st.code(result.stderr or "No output", language="text")

st.divider()
question = st.text_input("Ask a question about your documents:")
if question:
    with st.spinner("Thinking..."):
        answer = answer_question(question)
    st.write("**Answer:**")
    st.write(answer)