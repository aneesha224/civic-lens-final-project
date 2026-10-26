"""Credential-free checks for OpenAI-compatible provider request settings."""

from __future__ import annotations

import asyncio
import unittest

from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, ThinkingPart, UserPromptPart
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import MODEL_SETTINGS


class ModelConfigurationTests(unittest.TestCase):
    def test_portkey_cache_ids_are_not_replayed_to_responses_api(self) -> None:
        cache_id = "portkey_cache_27bd9764-2496-4463-872f-f011b496497e"
        model = OpenAIResponsesModel("gpt-6-luna", provider=OpenAIProvider(api_key="test"))
        history = [
            ModelResponse(
                [
                    ThinkingPart("cached reasoning", id=cache_id, provider_name="openai"),
                    TextPart("cached answer", id=cache_id, provider_name="openai"),
                ],
                provider_name="openai",
            ),
            ModelRequest([UserPromptPart("follow-up")]),
        ]

        async def map_history() -> list[dict[str, object]]:
            _, input_items = await model._map_messages(  # pyright: ignore[reportPrivateUsage]
                history,
                MODEL_SETTINGS,
                ModelRequestParameters(),
            )
            return input_items

        input_items = asyncio.run(map_history())

        self.assertFalse(any(item.get("id") == cache_id for item in input_items))
        self.assertFalse(any(item.get("type") == "reasoning" for item in input_items))


if __name__ == "__main__":
    unittest.main()
