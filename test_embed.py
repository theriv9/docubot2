# test_embed.py
from openai import AzureOpenAI
from dotenv import load_dotenv
import os
import re

load_dotenv()

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-04-01-preview")  # ← FIXED
)

text = """DocuBot is an AI-powered document Q&A system. It uses Azure AI Search for retrieval and Azure OpenAI for answers. This is a test document."""

text = re.sub(r'\s+', ' ', text).strip()

print(f"Testing embedding with: {text[:100]!r}...")
print(f"Model: {os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'embedding')}")

try:
    response = client.embeddings.create(
        input=text,  # ← STRING
        model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "embedding")  # ← DEPLOYMENT NAME
    )
    embedding = response.data[0].embedding
    print(f"SUCCESS! Embedding length: {len(embedding)}")
except Exception as e:
    print(f"FAILED: {e}")
    print(f"Check: Endpoint={os.getenv('AZURE_OPENAI_ENDPOINT')}")
    print(f"Model in Studio: Must be 'embedding' for text-embedding-ada-002")