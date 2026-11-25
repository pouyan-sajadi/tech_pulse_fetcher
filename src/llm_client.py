"""Synchronous client for OpenAI-compatible LLM gateways."""

import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class InvalidLLMResponse(ValueError):
    """The model response could not be read as a JSON object."""


class LLMClient:
    """Provider-agnostic LLM client configured through LLM_* variables."""

    def __init__(self) -> None:
        self.api_key = os.getenv("LLM_API_KEY")
        self.base_url = os.getenv("LLM_BASE_URL")
        self.model = os.getenv("LLM_MODEL")
        self._client = None

    def _get_client(self) -> OpenAI:
        missing = [
            name for name, value in (
                ("LLM_API_KEY", self.api_key),
                ("LLM_BASE_URL", self.base_url),
                ("LLM_MODEL", self.model),
            ) if not value
        ]
        if missing:
            raise ValueError("Missing required LLM configuration: " + ", ".join(missing))
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def chat_json(
        self, system_prompt: Any, user_message: Any, *, timeout: float | None = None
    ) -> dict[str, Any]:
        """Send a JSON-mode chat request and return its decoded object."""
        client = self._get_client()
        if timeout is not None:
            client = client.with_options(timeout=timeout, max_retries=0)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self._content(system_prompt)},
                {"role": "user", "content": self._content(user_message)},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            raise InvalidLLMResponse("Model returned an empty response")
        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise InvalidLLMResponse("Model response is not valid JSON") from exc
        if not isinstance(result, dict):
            raise InvalidLLMResponse("Model response must be a JSON object")
        return result

    @staticmethod
    def _content(value: Any) -> str:
        if isinstance(value, dict):
            return str(value.get("content", ""))
        return str(value)


llm_client = LLMClient()
