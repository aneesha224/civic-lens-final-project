"""Model and environment configuration."""

from __future__ import annotations

import os

from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


DEFAULT_MODEL = "gpt-6-luna"
MODEL_SETTINGS = {"openai_reasoning_effort": "none"}


class ModelConfigurationError(RuntimeError):
    """Raised when no credential is available for hosted analysis."""


def model_credentials_configured() -> bool:
    return any(os.getenv(name, "").strip() for name in ("PORTKEY_API_KEY", "OPENAI_API_KEY"))


def configured_model() -> Model | str:
    """Return a lazy PydanticAI model configuration."""
    model_name = os.getenv("AI_MODEL", DEFAULT_MODEL)
    portkey_key = os.getenv("PORTKEY_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if portkey_key and not openai_key:
        provider = OpenAIProvider(
            api_key=portkey_key,
            base_url=os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1"),
        )
        return OpenAIChatModel(model_name=model_name, provider=provider)
    if not (portkey_key or openai_key):
        raise ModelConfigurationError("No AI API credential is configured.")
    return model_name
