import json
from pathlib import Path
from typing import Any

import httpx

from notesolve.domain.models import NoteEditProposal
from notesolve.providers.openai_analyzer import _strict_schema


class OpenAIVaultNoteEditor:
    provider_name = "openai"
    prompt_version = "note-edit-v1"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 180,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required")
        self.model_name = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._transport = transport

    async def edit(self, *, current_content: str, instruction: str) -> NoteEditProposal:
        prompt_path = Path(__file__).resolve().parents[4] / "prompts" / "note_edit" / "v1.md"
        payload = {
            "model": self.model_name,
            "store": False,
            "instructions": prompt_path.read_text(encoding="utf-8"),
            "input": [{
                "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": json.dumps({
                        "instruction": instruction,
                        "current_markdown": current_content,
                    }, ensure_ascii=False),
                }],
            }],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "note_edit_proposal",
                    "description": "A complete revised Markdown note and concise change summary.",
                    "strict": True,
                    "schema": _strict_schema(NoteEditProposal.model_json_schema()),
                }
            },
        }
        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            transport=self._transport,
        ) as client:
            response = await client.post(
                "/responses",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )
            response.raise_for_status()
        return NoteEditProposal.model_validate_json(self._extract_output_text(response.json()))

    @staticmethod
    def _extract_output_text(payload: dict[str, Any]) -> str:
        for item in payload.get("output", []):
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for part in item.get("content", []):
                if isinstance(part, dict) and part.get("type") == "output_text":
                    text = part.get("text")
                    if isinstance(text, str) and text:
                        return text
        raise ValueError("OpenAI response did not contain structured output text")
