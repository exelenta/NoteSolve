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
                        confidence=0.85,
                    ),
                    confidence=0.85,
                )
            ],
        )


class FakeWorksheetVerifier:
    provider_name = "fake"
    model_name = "fake-verifier-v1"
    prompt_version = "verification-v1"

    async def verify(
        self,
        files: Sequence[InputFile],
        problem: ProblemResult,
        options: AnalyzeOptions,
    ) -> VerificationResult:
        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            method="independent_fake_check",
            details_markdown="독립 검산 결과 원래 풀이와 정답이 일치합니다.",
            confidence=0.99,
        )
