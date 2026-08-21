from collections.abc import Sequence

from notesolve.domain.models import (
    AnalyzeOptions,
    DocumentAnalysis,
    InputFile,
    ProblemResult,
    VerificationResult,
    VerificationStatus,
    WorksheetResult,
)


class FakeWorksheetAnalyzer:
    provider_name = "fake"
    model_name = "fake-worksheet-v1"
    prompt_version = "worksheet-v1"

    async def analyze(self, files: Sequence[InputFile], options: AnalyzeOptions) -> WorksheetResult:
        return WorksheetResult(
            document=DocumentAnalysis(subject=options.subject_hint or "math", confidence=0.99),
            problems=[
                ProblemResult(
                    id="sample-1",
                    number="1",
                    problem_type="short_answer",
                    question_markdown="Solve $x + 1 = 2$.",
                    solution_markdown="Subtract 1 from both sides.",
                    answer_markdown="$x = 1$",
                    verification=VerificationResult(
                        status=VerificationStatus.SELF_CHECKED,
                        method="substitution",
                        confidence=0.99,
                    ),
                    confidence=0.99,
                )
            ],
        )
