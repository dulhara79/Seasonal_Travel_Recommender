import os
import re
from typing import Dict, Any, List, Tuple, Optional
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain_core.documents import Document

# Assuming these are correct imports for your configuration
from server.utils.config import OPENAI_API_KEY, OPENAI_MODEL
from server.workflow.app_state import TripPlanState

LLM_MODEL = OPENAI_MODEL


# --- Helper Functions ---

def extract_url_and_question(query: str) -> tuple[str | None, str]:
    """
    Attempts to extract a URL and the remaining question from the user query.
    """
    # Regex pattern to find a URL
    url_pattern = r"(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})"

    match = re.search(url_pattern, query)

    if match:
        url = match.group(0).strip()
        question = query.replace(url, "").strip()
        # Clean up common instructions
        question = re.sub(
            r"(explore the given link and |paste link and asked question from that link|summarize it|from that link)",
            "", question, flags=re.IGNORECASE).strip()

        if not question:
            question = "Please summarize the content of this document."

        return url, question

    return None, query


def format_docs_for_state(docs: List[Document]) -> List[Dict[str, Any]]:
    """Converts LangChain Documents to a serializable List[Dict] for LangGraph state."""
    return [
        {
            "page_content": doc.page_content,
            "metadata": doc.metadata
        }
        for doc in docs
    ]


def docs_from_state_format(content: List[Dict[str, Any]]) -> List[Document]:
    """Converts a serializable List[Dict] back to LangChain Documents."""
    return [
        Document(
            page_content=item["page_content"],
            metadata=item["metadata"]
        )
        for item in content
    ]


def run_explorer_rag(url: str, question: str, content: Optional[List[Dict[str, Any]]] = None) -> Tuple[
    str, List[Document]]:
    """
    Core RAG logic to process a URL or resume from stored content, and answer a question.

    Returns: (final_answer, document_chunks)
    """

    splits: List[Document]

    if content:
        # Resume RAG: Recreate splits from stored state
        print("INFO: Recreating documents from state for RAG resumption.")
        splits = docs_from_state_format(content)
        if not splits:
            raise ValueError("Stored link content is empty or invalid.")
    else:
        # Initial RAG: Scrape the URL and create splits
        print(f"INFO: Loading content from the web page: {url}")
        loader = WebBaseLoader(url)
        documents = loader.load()

        if not documents:
            raise ValueError(f"Could not retrieve content from the URL: {url}.")

        print("INFO: Splitting content into chunks...")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(documents)

    # 4. Set up RAG Chain
    llm = ChatOpenAI(model=LLM_MODEL, temperature=0, api_key=OPENAI_API_KEY)
    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

    # Create a vector store from the chunks (in-memory, using Chroma)
    vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)
    retriever = vectorstore.as_retriever()

    # Create the RetrievalQA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=False
    )

    # 5. Get the final answer
    print(f"INFO: Invoking QA chain with question: {question}")
    result = qa_chain.invoke(question)

    final_answer = result.get("result", "Sorry, I was unable to generate a response based on the provided content.")

    return final_answer, splits

# === 7. Explorer Node ===
def explorer_agent_node(state: TripPlanState) -> Dict[str, Any]:
    """
    Handles RAG queries by visiting a link, storing content, and answering questions.
    """
    user_query = state["user_query"]
    current_url = state.get("current_link_url")
    link_content = state.get("current_link_content")

    # 1. Check for a new URL in the current query
    new_url, question = extract_url_and_question(user_query)

    # CASE A: A new URL is detected or the state is empty (clear previous context)
    if new_url and new_url != current_url:
        print(f"--- NODE: Explorer Agent Executing (NEW URL): {new_url}")
        state["current_link_url"] = new_url
        state["current_link_content"] = None  # Clear old content

        try:
            # New RAG: Scrape and generate answer/chunks
            answer, doc_chunks = run_explorer_rag(new_url, question, content=None)

            # Persist the content for future questions
            state["current_link_content"] = format_docs_for_state(doc_chunks)
            state["final_response"] = answer
            return state
        except Exception as e:
            # ... Error handling logic ...
            return state

    # CASE B: No new URL, but content is already in state (RESUME RAG)
    elif link_content:
        print(f"--- NODE: Explorer Agent Executing (RESUMED RAG) on {current_url}")

        try:
            # Resumed RAG: Use stored content to generate answer
            answer, _ = run_explorer_rag(current_url, user_query, content=link_content)
            state["final_response"] = answer
            return state
        except Exception as e:
            # ... Error handling logic ...
            return state

    # CASE C: No URL provided and no content stored (Fallback to Chat)
    else:
        # ... Fallback logic ...
        return state
