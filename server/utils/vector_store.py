import os
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

from server.utils.config import OPENAI_API_KEY, ORCHESTRATOR_CHROMA_DIR

# Initialize embeddings
embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

persist_path = ORCHESTRATOR_CHROMA_DIR
# persistent croma vector DB(data store locally)
vectorstore = Chroma(
    collection_name="orchestrator_memory",
    embedding_function=embeddings,
    persist_directory=persist_path
)

print(f"Chroma persisted at: {persist_path}")
print(os.listdir(persist_path))

print(f"Current working directory: {os.getcwd()}")
print(f"ChromaDB path: {os.path.abspath('chroma_db')}")


def add_texts_to_vectorstore(texts: list[str], metadatas: list[dict] = None):
    """Add texts with optional metadata to the vector DB."""
    vectorstore.add_texts(texts=texts, metadatas=metadatas)
    vectorstore.persist()

def get_vectorstore():
    """Return the initialized vectorstore."""
    return vectorstore
