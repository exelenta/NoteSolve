import base64
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import httpx

from notesolve.domain.models import AnalyzeOptions, InputFile, WorksheetResult
from notesolve.providers.openai_responses import OpenAIResponsesClient, ResponseUsage


def _strict_schema(node: object) -> object:
    if isinstance(node, dict):
        normalized = {key: _strict_schema(value) for key, value in node.items()}
        if normalized.get("type") == "object" or "properties" in normalized:
            normalized["additionalProperties"] = False
            properties = normalized.get("properties")
            if isinstance(properties, dict):
                normalized["required"] = list(properties.keys())
        return normalized
    if isinstance(node, list):
        return [_strict_schema(value) for value in node]
    return node


class OpenAIWorksheetAnalyzer:
    provider_name = "openai"
    prompt_version = "document-v2"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 180,
        max_retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required")
        self.model_name = model
        self._client = OpenAIResponsesClient(
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            transport=transport,
        )

    @property
    def last_usage(self) -> ResponseUsage:
        return self._client.last_usage

    async def analyze(self, files: Sequence[InputFile], options: AnalyzeOptions) -> WorksheetResult:
        if not files:
            raise ValueError("At least one worksheet file is required")
        content: list[dict[str, Any]] = [{"type": "input_text", "text": self._prompt(options)}]
        content.extend(self._file_input(file) for file in files)
        payload = {
            "model": self.model_name,
            "store": False,
            "input": [{"role": "user", "content": content}],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "study_document_result",
                    "description": "A source-faithful, subject-aware Markdown study document.",
                    "strict": True,
                    "schema": _strict_schema(WorksheetResult.model_json_schema()),
                }
            },
        }
        response = await self._client.create(payload)
        return WorksheetResult.model_validate_json(self._extract_output_text(response))

    @staticmethod
    def _file_input(file: InputFile) -> dict[str, Any]:
        encoded = base64.b64encode(file.content).decode("ascii")
        if file.content_type.startswith("image/"):
            return {
                "type": "input_image",
                "image_url": f"data:{file.content_type};base64,{encoded}",
                "detail": "high",
            }
        if file.content_type == "application/pdf":
            return {
                "type": "input_file",
                "filename": file.original_filename,
                "file_data": encoded,
            }
        raise ValueError(f"Unsupported worksheet content type: {file.content_type}")

    @staticmethod
    def _extract_output_text(payload: Mapping[str, Any]) -> str:
        for item in payload.get("output", []):
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for part in item.get("content", []):
                if isinstance(part, dict) and part.get("type") == "output_text":
                    text = part.get("text")
                    if isinstance(text, str) and text:
                        return text
        raise ValueError("OpenAI response did not contain structured output text")

    @staticmethod
    def _prompt(options: AnalyzeOptions) -> str:
        prompt_path = Path(__file__).resolve().parents[4] / "prompts" / "document" / "v2.md"
        prompt = prompt_path.read_text(encoding="utf-8")
        context = {
            "language": options.language,
            "subject_hint": options.subject_hint or "unknown",
            "help_level": options.help_level.value,
            "output_style": options.output_style.value,
            "custom_instruction": options.custom_instruction or "none",
        }
        return f"{prompt}\n\nRuntime context:\n{json.dumps(context, ensure_ascii=False)}"
