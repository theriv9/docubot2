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
import PyPDF2
import glob

load_dotenv()

# Config
ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = "docubot-index"
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
EMBEDDING_MODEL = "text-embedding-ada-002"

credential = AzureKeyCredential(KEY)
index_client = SearchIndexClient(ENDPOINT, credential)
search_client = SearchClient(ENDPOINT, INDEX_NAME, credential)

# Azure OpenAI for embeddings
embed_client = AzureOpenAI(
    azure_endpoint=OPENAI_ENDPOINT,
    api_key=OPENAI_KEY,
    api_version="2024-02-01"
)

def get_embedding(text):
    return embed_client.embeddings.create(input=text, model=EMBEDDING_MODEL).data[0].embedding

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
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i+size])
        chunks.append(chunk)
        i += size - overlap
    return chunks

def extract_pdf_text(path):
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        return " ".join(page.extract_text() or "" for page in reader.pages)

def ingest_pdfs():
    create_index()
    pdf_files = glob.glob("docs/*.pdf")
    if not pdf_files:
        print("No PDFs in /docs folder! Add some and rerun.")
        return

    docs = []
    for pdf in pdf_files:
        print(f"Processing {pdf}...")
        text = extract_pdf_text(pdf)
        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            docs.append({
                "id": f"{os.path.basename(pdf)}_{i}",
                "content": chunk,
                "source": os.path.basename(pdf),
                "content_vector": get_embedding(chunk)
            })
    search_client.upload_documents(docs)
    print(f"Uploaded {len(docs)} chunks from {len(pdf_files)} PDFs")

if __name__ == "__main__":
    os.makedirs("docs", exist_ok=True)
    ingest_pdfs()