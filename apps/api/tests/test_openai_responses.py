import httpx
import pytest
from notesolve.providers.openai_responses import OpenAIRequestError, OpenAIResponsesClient


@pytest.mark.asyncio
async def test_responses_client_retries_transient_error_and_tracks_usage() -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"retry-after": "0"})
        return httpx.Response(
            200,
            json={
                "output": [],
                "usage": {
                    "input_tokens": 120,
                    "output_tokens": 30,
                    "total_tokens": 150,
                },
            },
        )

    client = OpenAIResponsesClient(
        api_key="test-key",
        base_url="https://api.openai.test/v1",
        timeout_seconds=1,
        max_retries=2,
        transport=httpx.MockTransport(handler),
    )
    await client.create({"model": "test"})
    assert attempts == 2
    assert client.last_usage.input_tokens == 120
    assert client.last_usage.output_tokens == 30
    assert client.last_usage.total_tokens == 150


@pytest.mark.asyncio
async def test_responses_client_exposes_sanitized_api_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "Invalid file_data value"}})

    client = OpenAIResponsesClient(
        api_key="test-key",
        base_url="https://api.openai.test/v1",
        timeout_seconds=1,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(OpenAIRequestError, match="Invalid file_data value"):
        await client.create({"model": "test"})
