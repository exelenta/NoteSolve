from uuid import UUID

from notesolve.application.markdown import build_vault_preview
from notesolve.domain.models import (
    DocumentAnalysis,
    ProblemResult,
    VerificationResult,
    VerificationStatus,
    WorksheetResult,
)


def test_vault_preview_sanitizes_path_and_preserves_latex() -> None:
    preview = build_vault_preview(
        document_id=UUID("12345678-0000-0000-0000-000000000000"),
        original_filename="../chapter:1?.png",
        result=WorksheetResult(
            document=DocumentAnalysis(
                subject="수학/대수",
                unit="방정식: 기초",
                confidence=0.95,
            ),
            problems=[ProblemResult(
                id="1",
                number="1",
                problem_type="short_answer",
                question_markdown="$x^2=4$",
                solution_markdown="$x=\\pm2$",
                answer_markdown="$x=2,-2$",
                verification=VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="substitution",
                    confidence=0.99,
                ),
                concepts=["이차 방정식"],
                confidence=0.95,
            )],
        ),
    )
    operation = preview.operations[0]
    assert operation.path == "NoteSolve/수학-대수/방정식- 기초/chapter-1-12345678.md"
    assert ".." not in operation.path
    assert "$x=\\pm2$" in (operation.content or "")
    assert "#이차-방정식" in (operation.content or "")
