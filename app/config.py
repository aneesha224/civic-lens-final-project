"""Model and environment configuration."""

from __future__ import annotations

import os

from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


DEFAULT_MODEL = "gpt-6-luna"
# Keep each provider response bounded; workflow-level UsageLimits add a second
# guard on cumulative requests and tokens within each specialist run.
MODEL_SETTINGS = {
    "openai_reasoning_effort": "none",
    # Portkey cache item IDs are not valid Azure Responses item IDs.
    "openai_send_reasoning_ids": False,
    "max_tokens": 3500,
}


class ModelConfigurationError(RuntimeError):
    """Raised when no credential is available for hosted analysis."""


def model_credentials_configured() -> bool:
    return any(os.getenv(name, "").strip() for name in ("PORTKEY_API_KEY", "OPENAI_API_KEY"))


def configured_model() -> Model | str:
    """Return a lazy PydanticAI model configuration."""
    model_name = os.getenv("AI_MODEL", "").strip() or DEFAULT_MODEL
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    portkey_key = os.getenv("PORTKEY_API_KEY", "").strip()
    # Prefer a direct OpenAI key when one is configured; fall back to Portkey.
    if openai_key:
        provider = OpenAIProvider(api_key=openai_key)
        return OpenAIChatModel(model_name=model_name, provider=provider)
    if portkey_key:
        provider = OpenAIProvider(
            api_key=portkey_key,
            base_url=os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1"),
        )
        return OpenAIChatModel(model_name=model_name, provider=provider)
    raise ModelConfigurationError("No AI API credential is configured.")
