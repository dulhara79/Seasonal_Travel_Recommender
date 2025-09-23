from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from regex import search

from server.agents.orchestrator_agent.vector_store import get_vectorstore
from server.utils.config import OPENAI_API_KEY, OPENAI_MODEL

# Initialize LLM
llm = ChatOpenAI(api_key=OPENAI_API_KEY, model=OPENAI_MODEL, temperature=0)

# create retriever
vectorstore = get_vectorstore()
retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})

# Build RetrievalQA chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    return_source_documents=True,
    chain_type_kwargs={"verbose": True}
)

def retrieve_relevant_context(query: str, top_k: int = 3) -> str:
    """Retrieve relevant context from vector DB for a query."""
    docs = retriever.get_relevant_documents(query)
    if not docs:
        return ""
    return "\n".join([doc.page_content for doc in docs])
