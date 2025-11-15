# ingest_pdf.py
import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, SearchFieldDataType, VectorSearch,
    HnswAlgorithmConfiguration, VectorSearchProfile, SimpleField, SearchableField
)
from openai import AzureOpenAI
from dotenv import load_dotenv
import pdfplumber
import glob
import re

load_dotenv()

# Config
ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = "docubot-index"
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "embedding")

credential = AzureKeyCredential(KEY)
index_client = SearchIndexClient(ENDPOINT, credential)
search_client = SearchClient(ENDPOINT, INDEX_NAME, credential)

embed_client = AzureOpenAI(
    azure_endpoint=OPENAI_ENDPOINT,
    api_key=OPENAI_KEY,
    api_version="2024-02-01"
)

def get_embedding(text):
    # 1. FORCE STRING
    if isinstance(text, (list, tuple)):
        text = " ".join(str(t) for t in text if t)
    elif not isinstance(text, str):
        text = str(text)

    # 2. CLEAN: Remove \n, \r, extra spaces, non-UTF8
    import re
    text = re.sub(r'\s+', ' ', text)  # Collapse whitespace
    text = text.strip()
    if not text:
        return [0.0] * 1536

    # 3. TRUNCATE
    if len(text) > 8000:
        text = text[:8000]

    print(f"[DEBUG] Embedding input ({len(text)} chars): {text[:100]!r}...")

    try:
        # ← USE STRING, NOT LIST
        response = embed_client.embeddings.create(
            input=text,
            model=EMBEDDING_DEPLOYMENT
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"[ERROR] Embedding failed: {e}")
        return [0.0] * 1536
     
def create_index():
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchableField(name="source", type=SearchFieldDataType.String),
        SearchField(name="content_vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    vector_search_dimensions=1536, vector_search_profile_name="hnsw-profile")
    ]
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw", parameters={"metric": "cosine"})],
        profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw")]
    )
    index = SearchIndex(name=INDEX_NAME, fields=fields, vector_search=vector_search)
    index_client.create_or_update_index(index)
    print(f"Index '{INDEX_NAME}' ready")

def chunk_text(text, size=800, overlap=100):
    if not isinstance(text, str):
        text = str(text)
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + size])
        chunks.append(chunk)
        i += size - overlap
    return chunks

def extract_pdf_text(path):
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error reading {path}: {e}")
    return text.strip()

def ingest_pdfs():
    create_index()
    pdf_files = glob.glob("docs/*.pdf")
    if not pdf_files:
        print("No PDFs in /docs folder! Add TEST.pdf and rerun.")
        return

    docs = []
    for pdf in pdf_files:
        print(f"Processing {pdf}...")
        text = extract_pdf_text(pdf)
        if not text:
            print(f"Warning: No text extracted from {pdf}")
            continue
        chunks = chunk_text(text)
        safe_filename = os.path.basename(pdf).replace(".", "_")
        for i, chunk in enumerate(chunks):
            if not isinstance(chunk, str):
                chunk = str(chunk)
            docs.append({
                "id": f"{safe_filename}_{i}",
                "content": chunk,
                "source": os.path.basename(pdf),
                "content_vector": get_embedding(chunk)
            })
    if docs:
        search_client.upload_documents(docs)
        print(f"Uploaded {len(docs)} chunks from {len(pdf_files)} PDFs")
    else:
        print("No documents uploaded.")

if __name__ == "__main__":
    os.makedirs("docs", exist_ok=True)
    ingest_pdfs()