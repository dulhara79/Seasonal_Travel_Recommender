# summary_refiner.py

from typing import Optional, Any, Dict

# Lazy imports for LangChain components
try:
    from pydantic import SecretStr  # Import SecretStr for correct type hinting
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_openai import ChatOpenAI
    from langchain.chains import LLMChain

    # Define a custom Type Alias to resolve the 'Cannot find reference' issue
    # when LLMChain is successfully imported.
    RefinementChain = LLMChain
except ImportError:
    # Set all imports to None if LangChain is missing
    SecretStr = str
    ChatPromptTemplate = None
    StrOutputParser = None
    ChatOpenAI = None
    LLMChain = None
    # Use a safe fallback type if imports fail
    RefinementChain = Any

# Assuming OPENAI_API_KEY and OPENAI_MODEL are imported and available
from server.utils.config import OPENAI_API_KEY, OPENAI_MODEL


def get_summary_refinement_chain(
        api_key: Optional[str] = OPENAI_API_KEY,
        model_name: Optional[str] = OPENAI_MODEL
) -> Optional[RefinementChain]:
    """
    Initializes and returns the Summary Refinement LLMChain.

    Args:
        api_key: The OpenAI API key. Expected type is SecretStr or str.
        model_name: The OpenAI model name.

    Returns:
        An LLMChain instance wrapped in RefinementChain type, or None if dependencies are missing.
    """

    # 1. Type Hint Fix: Correctly define the expected type for the return value
    # The return type is Optional[LLMChain] or the alias RefinementChain.
    if not all([ChatPromptTemplate, StrOutputParser, ChatOpenAI, LLMChain]):
        print("WARNING: LangChain dependencies not installed. Cannot create refinement chain.")
        # Fix 2: Function 'get_summary_refinement_chain' doesn't return anything
        # It DOES return None here, which satisfies the Optional[RefinementChain] type.
        return None

    summary_refinement_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                You are a skilled and friendly document editor. Your task is to apply the 'USER FEEDBACK' 
                to the 'PREVIOUS SUMMARY' while strictly adhering to the original facts.

                **Rules for Refinement:**
                1. Maintain Factual Accuracy — do NOT invent or alter trip details.
                2. Focus on Style — apply changes to tone, length, formatting, clarity.
                3. Preserve Disclaimers — keep 'Responsible AI & Data Notes' section unchanged.
                4. Output Format — return ONLY the refined Markdown summary.
                """,
            ),
            ("human", "PREVIOUS SUMMARY:\n{previous_summary}\n\nUSER FEEDBACK: {user_feedback}"),
        ]
    )

    # Note on Fix 1: LLMChain components internally handle SecretStr/str conversion.
    # By setting the function argument type hint to Optional[str], we satisfy the
    # linter that was flagging OPENAI_API_KEY (which is likely a string from config).
    llm = ChatOpenAI(api_key=api_key, model=model_name, temperature=0.5, max_tokens=1000)

    return LLMChain(
        llm=llm,
        prompt=summary_refinement_prompt,
        output_parser=StrOutputParser(),
        verbose=False
    )


def refine_summary(
        previous_summary: str,
        user_feedback: str,
        api_key: Optional[str] = OPENAI_API_KEY,
        model_name: Optional[str] = OPENAI_MODEL,
) -> str:
    """Runs the refinement chain and returns the new summary text."""
    chain = get_summary_refinement_chain(api_key, model_name)

    # Fix 4: 'None' object is not callable
    # The 'if chain is None' check resolves this by ensuring 'chain' is only called if initialization succeeded.
    if chain is None:
        return "⚠️ Refinement service is unavailable (LangChain missing or config error)."

    try:
        # Fix 3: Cannot find reference 'invoke' in 'Never'
        # The introduction of the type alias RefinementChain = LLMChain
        # (and using Optional[RefinementChain] as the return type for get_summary_refinement_chain)
        # helps the static analyzer correctly identify that 'chain' *is* an LLMChain, which has an '.invoke()' method.

        # LLMChain's .invoke() returns a dictionary when an output_parser is set.
        result: Dict[str, Any] = chain.invoke({
            "previous_summary": previous_summary,
            "user_feedback": user_feedback
        })

        # result is dict → extract "text"
        return result.get("text", str(result))
    except Exception as e:
        # Fix 5: This code is unreachable
        # The 'except' block is always reachable in Python and serves as necessary error handling
        # for API calls, network issues, or internal LLM errors.
        return f"⚠️ Error during summary refinement: {e}"