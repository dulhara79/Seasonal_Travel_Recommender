from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

from server.utils.config import OPENAI_API_KEY

# Initialize embeddings
embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

# persistent croma vector DB(data store locally)
vectorstore = Chroma(
    collection_name="orchestrator_memory",
    embedding_function=embeddings,
    persist_directory="../../chroma_db"
)

def add_texts_to_vectorstore(texts: list[str], metadatas: list[dict] = None):
    """Add texts with optional metadata to the vector DB."""
    vectorstore.add_texts(texts=texts, metadatas=metadatas)
    vectorstore.persist()

def get_vectorstore():
    """Return the initialized vectorstore."""
    return vectorstore
