import base64
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import httpx

from notesolve.domain.models import AnalyzeOptions, InputFile, ProblemResult, VerificationResult
from notesolve.providers.openai_analyzer import _strict_schema
from notesolve.providers.openai_responses import OpenAIResponsesClient, ResponseUsage


class OpenAIWorksheetVerifier:
    provider_name = "openai"
    prompt_version = "verification-v1"

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

    async def verify(
        self,
        files: Sequence[InputFile],
        problem: ProblemResult,
        options: AnalyzeOptions,
    ) -> VerificationResult:
        if not files:
            raise ValueError("At least one worksheet file is required")
        content: list[dict[str, Any]] = [{
            "type": "input_text",
            "text": self._prompt(problem, options),
        }]
        content.extend(self._file_input(file) for file in files)
        payload = {
            "model": self.model_name,
            "store": False,
            "input": [{"role": "user", "content": content}],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "verification_result",
                    "description": "An independent check of one worksheet solution.",
                    "strict": True,
                    "schema": _strict_schema(VerificationResult.model_json_schema()),
                }
            },
        }
        response = await self._client.create(payload)
        output = self._extract_output_text(response)
        return VerificationResult.model_validate_json(output)

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

    @staticmethod
    def _prompt(problem: ProblemResult, options: AnalyzeOptions) -> str:
        path = Path(__file__).resolve().parents[4] / "prompts" / "verification" / "v1.md"
        prompt = path.read_text(encoding="utf-8")
        context = {
            "language": options.language,
            "problem": problem.model_dump(mode="json"),
        }
        return f"{prompt}\n\nCandidate to verify:\n{json.dumps(context, ensure_ascii=False)}"
