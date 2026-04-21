from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def estimate_tokens(text: str) -> int:
    compact = " ".join(text.split())
    if not compact:
        return 0
    return max(1, len(compact) // 4)


@dataclass
class DraftResponse:
    provider: str
    model: str
    content: str
    prompt_tokens: int
    completion_tokens: int
    raw_response: dict[str, Any] | None = None


class LLMProvider(Protocol):
    provider_name: str
    model_name: str

    def generate(
        self,
        *,
        field_name: str,
        prompt: str,
    ) -> DraftResponse: ...


class MockLLMProvider:
    provider_name = "mock"
    model_name = "mock-static"

    def __init__(self, responses: list[Any] | tuple[Any, ...] | str | tuple[Any, ...]) -> None:
        if isinstance(responses, (list, tuple)):
            self._responses = list(responses)
        else:
            self._responses = [responses]

    def generate(
        self,
        *,
        field_name: str,
        prompt: str,
    ) -> DraftResponse:
        del field_name
        item = self._responses[0] if len(self._responses) == 1 else self._responses.pop(0)
        prompt_tokens = estimate_tokens(prompt)
        completion_tokens = 0
        content = ""

        if isinstance(item, tuple):
            if len(item) == 3:
                content, prompt_tokens, completion_tokens = item
            elif len(item) == 2:
                content, completion_tokens = item
            else:
                raise ValueError("mock response tuple must be (content, completion_tokens) or (content, prompt_tokens, completion_tokens)")
        else:
            content = str(item)
        if completion_tokens == 0:
            completion_tokens = estimate_tokens(content)

        return DraftResponse(
            provider=self.provider_name,
            model=self.model_name,
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw_response={"provider": self.provider_name},
        )


class OpenAIChatProvider:
    provider_name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        base_url: str = "https://api.openai.com",
    ) -> None:
        self._api_key = api_key
        self.model_name = model_name
        self._base_url = base_url.rstrip("/")

    def generate(
        self,
        *,
        field_name: str,
        prompt: str,
    ) -> DraftResponse:
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You draft KiU skill fields. Return only the requested field body as plain Markdown, without headings or code fences."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        }
        response_doc = _post_json(
            f"{self._base_url}/v1/chat/completions",
            payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        content = _extract_openai_content(response_doc)
        usage = response_doc.get("usage", {})
        return DraftResponse(
            provider=self.provider_name,
            model=self.model_name,
            content=_normalize_content(content, field_name),
            prompt_tokens=int(usage.get("prompt_tokens", estimate_tokens(prompt))),
            completion_tokens=int(usage.get("completion_tokens", estimate_tokens(content))),
            raw_response=response_doc,
        )


class OllamaChatProvider:
    provider_name = "ollama"

    def __init__(
        self,
        *,
        model_name: str,
        base_url: str = "http://localhost:11434",
    ) -> None:
        self.model_name = model_name
        self._base_url = base_url.rstrip("/")

    def generate(
        self,
        *,
        field_name: str,
        prompt: str,
    ) -> DraftResponse:
        payload = {
            "model": self.model_name,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You draft KiU skill fields. Return only the requested field body as plain Markdown, without headings or code fences."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        }
        response_doc = _post_json(
            f"{self._base_url}/api/chat",
            payload,
            headers={"Content-Type": "application/json"},
        )
        message = response_doc.get("message", {})
        content = str(message.get("content", ""))
        return DraftResponse(
            provider=self.provider_name,
            model=self.model_name,
            content=_normalize_content(content, field_name),
            prompt_tokens=int(response_doc.get("prompt_eval_count", estimate_tokens(prompt))),
            completion_tokens=int(response_doc.get("eval_count", estimate_tokens(content))),
            raw_response=response_doc,
        )


def create_provider_from_env() -> LLMProvider:
    provider = os.getenv("KIU_LLM_PROVIDER", "").strip().lower()
    if not provider:
        raise ValueError("KIU_LLM_PROVIDER is required when drafting_mode=llm-assisted")

    if provider == "mock":
        response = os.getenv("KIU_LLM_MOCK_RESPONSE")
        if response is None:
            raise ValueError("KIU_LLM_MOCK_RESPONSE is required for KIU_LLM_PROVIDER=mock")
        return MockLLMProvider(response)

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for KIU_LLM_PROVIDER=openai")
        model_name = os.getenv("KIU_OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.getenv("KIU_OPENAI_BASE_URL", "https://api.openai.com")
        return OpenAIChatProvider(
            api_key=api_key,
            model_name=model_name,
            base_url=base_url,
        )

    if provider == "ollama":
        model_name = os.getenv("KIU_OLLAMA_MODEL")
        if not model_name:
            raise ValueError("KIU_OLLAMA_MODEL is required for KIU_LLM_PROVIDER=ollama")
        base_url = os.getenv("KIU_OLLAMA_BASE_URL", "http://localhost:11434")
        return OllamaChatProvider(
            model_name=model_name,
            base_url=base_url,
        )

    raise ValueError(f"unsupported KIU_LLM_PROVIDER: {provider}")


def _post_json(url: str, payload: dict[str, Any], *, headers: dict[str, str]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:  # pragma: no cover
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"provider request failed: {exc.code} {body}") from exc
    except URLError as exc:  # pragma: no cover
        raise RuntimeError(f"provider request failed: {exc}") from exc


def _extract_openai_content(response_doc: dict[str, Any]) -> str:
    choices = response_doc.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        fragments = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                fragments.append(str(item.get("text", "")))
        return "".join(fragments)
    return str(content)


def _normalize_content(content: str, field_name: str) -> str:
    stripped = content.strip()
    fenced_prefix = "```"
    if stripped.startswith(fenced_prefix):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == fenced_prefix:
            stripped = "\n".join(lines[1:-1]).strip()
    header = f"## {field_name}"
    if stripped.startswith(header):
        stripped = stripped[len(header):].strip()
    return stripped
