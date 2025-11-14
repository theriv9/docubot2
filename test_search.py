import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, SearchFieldDataType, VectorSearch,
    HnswAlgorithmConfiguration, VectorSearchProfile, SimpleField
)
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
key = os.getenv("AZURE_SEARCH_KEY")
index_name = "docubot2-test-index"

credential = AzureKeyCredential(key)
index_client = SearchIndexClient(endpoint, credential)
search_client = SearchClient(endpoint, index_name, credential)

def create_index():
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchField(name="content", type=SearchFieldDataType.String, searchable=True),
        SearchField(name="content_vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    vector_search_dimensions=1536, vector_search_profile_name="hnsw-profile")
    ]
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw", parameters={"metric": "cosine"})],
        profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw")]
    )
    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
    index_client.create_or_update_index(index)
    print("Index created")

def upload_doc():
    doc = {"id": "test1", "content": "Azure AI Search powers DocuBot.", "content_vector": [0.1]*1536}
    search_client.upload_documents([doc])
    print("Doc uploaded")

def search():
    results = search_client.search(search_text="DocuBot")
    print("\nResults:")
    for r in results:
        print(r["content"])

if __name__ == "__main__":
    create_index()
    upload_doc()
    search()