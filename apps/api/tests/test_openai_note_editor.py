import json

import httpx
import pytest
from notesolve.providers.openai_note_editor import OpenAIVaultNoteEditor


@pytest.mark.asyncio
async def test_openai_note_editor_uses_instructions_and_structured_output() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert "current_markdown" in payload["input"][0]["content"][0]["text"]
        assert payload["text"]["format"]["name"] == "note_edit_proposal"
        assert "Never propose" in payload["instructions"]
        proposal = {
            "content": "# Math\n\nDetailed solution.",
            "summary": "Expanded the solution.",
        }
        return httpx.Response(
            200,
            json={
                "output": [{
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(proposal)}],
                }]
            },
        )

    editor = OpenAIVaultNoteEditor(
        api_key="test-key",
        model="test-model",
        base_url="https://api.openai.test/v1",
        transport=httpx.MockTransport(handler),
    )
    proposal = await editor.edit(
        current_content="# Math",
        instruction="Expand the solution.",
    )
    assert proposal.content.endswith("Detailed solution.")
    assert proposal.summary == "Expanded the solution."
