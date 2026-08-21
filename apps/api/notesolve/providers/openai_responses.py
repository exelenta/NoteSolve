import asyncio
from dataclasses import dataclass
from typing import Any, cast

import httpx


class OpenAIRequestError(RuntimeError):
    """A sanitized error returned by the OpenAI API."""


def _error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return str(error["message"])[:1000]
    return f"OpenAI API request failed with status {response.status_code}"


@dataclass(frozen=True)
class ResponseUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: "ResponseUsage") -> "ResponseUsage":
        return ResponseUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


class OpenAIResponsesClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout_seconds: float,
        max_retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._transport = transport
        self.last_usage = ResponseUsage()

    async def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            transport=self._transport,
        ) as client:
            for attempt in range(self._max_retries + 1):
                response = await client.post(
                    "/responses",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
                if response.status_code not in {408, 409, 429} and response.status_code < 500:
                    if response.is_error:
                        raise OpenAIRequestError(_error_message(response))
                    body = cast(dict[str, Any], response.json())
                    self.last_usage = self._parse_usage(body)
                    return body
                if attempt == self._max_retries:
                    raise OpenAIRequestError(_error_message(response))
                retry_after = response.headers.get("retry-after")
                delay = min(float(retry_after), 5.0) if retry_after else 0.25 * (2**attempt)
                await asyncio.sleep(delay)
        raise RuntimeError("OpenAI response retry loop exited unexpectedly")

    @staticmethod
    def _parse_usage(payload: dict[str, Any]) -> ResponseUsage:
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            return ResponseUsage()
        return ResponseUsage(
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            total_tokens=int(usage.get("total_tokens", 0)),
        )


def usage_of(provider: object) -> ResponseUsage:
    usage = getattr(provider, "last_usage", None)
    return usage if isinstance(usage, ResponseUsage) else ResponseUsage()
