import json

import httpx
import pytest
from notesolve.domain.models import (
    AnalyzeOptions,
    InputFile,
    ProblemResult,
    VerificationResult,
    VerificationStatus,
)
from notesolve.providers.openai_verifier import OpenAIWorksheetVerifier


@pytest.mark.asyncio
async def test_openai_verifier_checks_source_and_parses_structured_result() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        content = payload["input"][0]["content"]
        assert "Candidate to verify" in content[0]["text"]
        assert content[1]["type"] == "input_image"
        assert payload["text"]["format"]["name"] == "verification_result"
        result = {
            "status": "conflict",
            "method": "independent substitution",
            "details_markdown": "Substitution gives $3 \\ne 4$.",
            "confidence": 0.98,
        }
        return httpx.Response(
            200,
            json={
                "output": [{
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(result)}],
                }]
            },
        )

    verifier = OpenAIWorksheetVerifier(
        api_key="test-key",
        model="test-model",
        base_url="https://api.openai.test/v1",
        transport=httpx.MockTransport(handler),
    )
    verification = await verifier.verify(
        [InputFile(
            storage_key="worksheet.png",
            content_type="image/png",
            original_filename="worksheet.png",
            content=b"image-data",
        )],
        ProblemResult(
            id="1",
            question_markdown="$x+1=4$",
            solution_markdown="$x=2$",
            answer_markdown="$x=2$",
            problem_type="short_answer",
            verification=VerificationResult(
                status=VerificationStatus.SELF_CHECKED,
                confidence=0.7,
            ),
            confidence=0.7,
            needs_review=True,
        ),
        AnalyzeOptions(),
    )
    assert verification.status == VerificationStatus.CONFLICT
    assert verification.confidence == 0.98
