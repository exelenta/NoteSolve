import json

import httpx
import pytest
from notesolve.domain.models import AnalyzeOptions, InputFile
from notesolve.providers.openai_analyzer import OpenAIWorksheetAnalyzer


@pytest.mark.asyncio
async def test_openai_analyzer_sends_image_and_parses_structured_result() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        content = payload["input"][0]["content"]
        assert content[1]["type"] == "input_image"
        assert content[1]["image_url"].startswith("data:image/png;base64,")
        assert payload["text"]["format"]["type"] == "json_schema"
        result = {
            "schema_version": 1,
            "document": {
                "subject": "math",
                "unit": "linear equations",
                "confidence": 0.99,
                "warnings": [],
            },
            "problems": [
                {
                    "id": "1",
                    "number": "1",
                    "problem_type": "short_answer",
                    "question_markdown": "$x+1=2$",
                    "solution_markdown": "Subtract 1.",
                    "answer_markdown": "$x=1$",
                    "verification": {
                        "status": "self_checked",
                        "method": "substitution",
                        "details_markdown": None,
                        "confidence": 0.99,
                    },
                    "concepts": ["linear equations"],
                    "warnings": [],
                    "confidence": 0.99,
                    "needs_review": False,
                }
            ],
        }
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps(result)}],
                    }
                ]
            },
        )

    analyzer = OpenAIWorksheetAnalyzer(
        api_key="test-key",
        model="test-model",
        base_url="https://api.openai.test/v1",
        transport=httpx.MockTransport(handler),
    )
    result = await analyzer.analyze(
        [
            InputFile(
                storage_key="worksheet.png",
                content_type="image/png",
                original_filename="worksheet.png",
                content=b"image-data",
            )
        ],
        AnalyzeOptions(subject_hint="math"),
    )
    assert result.document.subject == "math"
    assert result.problems[0].answer_markdown == "$x=1$"
