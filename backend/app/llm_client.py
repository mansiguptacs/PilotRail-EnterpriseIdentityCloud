import os

from langchain_openai import ChatOpenAI

XAI_API_BASE = os.getenv("XAI_API_BASE", "https://api.x.ai/v1")
DEFAULT_XAI_MODEL = "grok-3-mini"


def xai_api_key() -> str:
    return os.getenv("XAI_API_KEY", "").strip()


def xai_model() -> str:
    return os.getenv("XAI_MODEL", DEFAULT_XAI_MODEL).strip() or DEFAULT_XAI_MODEL


def get_chat_llm() -> ChatOpenAI | None:
    """Return a LangChain chat client for xAI Grok (OpenAI-compatible API)."""
    api_key = xai_api_key()
    if not api_key:
        return None
    return ChatOpenAI(
        model=xai_model(),
        temperature=0,
        api_key=api_key,
        base_url=XAI_API_BASE,
        max_retries=1,
    )


def model_label() -> str:
    return xai_model()
