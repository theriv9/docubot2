# app.py
import streamlit as st
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI
from dotenv import load_dotenv
import os

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
    return llm.embeddings.create(input=text, model="text-embedding-ada-002").data[0].embedding

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

with st.sidebar:
    st.header("Upload PDFs")
    uploaded = st.file_uploader("Drop PDFs here", type="pdf", accept_multiple_files=True)
    if st.button("Index Documents") and uploaded:
        os.makedirs("docs", exist_ok=True)
        for f in uploaded:
            with open(f"docs/{f.name}", "wb") as out:
                out.write(f.getbuffer())
        st.success("Saved! Run `python ingest_pdf.py` in terminal.")
        st.info("After indexing, refresh and ask questions!")

st.divider()
question = st.text_input("Ask a question about your documents:")
if question:
    with st.spinner("Thinking..."):
        answer = answer_question(question)
    st.write("**Answer:**")
    st.write(answer)