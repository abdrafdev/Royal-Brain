from __future__ import annotations

from openai import OpenAI

from app.core.config import get_settings


def get_openai_client() -> OpenAI | None:
    """Return configured OpenAI client or None if key not set."""
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    return OpenAI(api_key=settings.openai_api_key)
