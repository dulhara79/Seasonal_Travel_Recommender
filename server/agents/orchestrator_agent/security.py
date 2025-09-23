import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import Optional

from server.agents.orchestrator_agent.vector_store import add_texts_to_vectorstore

# Character limit (2000 chars max)
SAFE_TEXT_PATTERNS = re.compile(r"^[\s\S]{0,2000}$")

# Word limit (e.g., 300 words max)
MAX_WORDS = 300

def sanitize_input(text: Optional[str]) -> str:
    """Sanitize input to prevent XSS, SQLi, and script injection.
    Safely handles None/empty input by returning an empty string.
    """
    if not text:
        print('Debug: sanitize_input received empty or None input.')
        return ""

    # # Input size validation
    # if not SAFE_TEXT_PATTERNS.match(text):
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Invalid Input Size."
    #     )
    #
    # # Word limit check
    # if len(text.split()) > MAX_WORDS:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Input exceeds maximum word limit."
    #     )

    print(f"\nDebug: Original input length: {len(text)} characters, {len(text.split())} words")

    # Remove HTML/JS script tags
    text = re.sub(r"(?i)<\s*script.*?>.*?<\s*/\s*script\s*>", "", text)

    # Remove inline JavaScript and suspicious URIs
    text = re.sub(r"(?i)javascript:", "", text)
    text = re.sub(r"(?i)data:text/html", "", text)

    # Remove SQL injection keywords (basic protection)
    sql_patterns = r"(?i)\b(SELECT|UPDATE|DELETE|INSERT|DROP|ALTER|TRUNCATE|EXEC)\b"
    text = re.sub(sql_patterns, "", text)

    # Remove command injection patterns
    cmd_patterns = r"(\|\||;|&&|`|\$\(.*?\))"
    text = re.sub(cmd_patterns, "", text)

    # Normalize whitespace (prevent obfuscation)
    text = re.sub(r"\s+", " ", text).strip()

    # if exceed word limit chunk + store in vector DB
    if len(text.split()) > MAX_WORDS:
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        # print(f"\nWord Splitting into chunks for storage. Total words: {len(text.split())}\n{splitter}")
        chunks = splitter.split_text(text)
        # print(f"\nChunks: {chunks}\n")
        for i, chunk in enumerate(chunks):
            add_texts_to_vectorstore([chunk], metadatas=[{"chunk_id": i}])
        return "LONG_INPUT_STORED"

    return text
