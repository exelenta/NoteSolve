from uuid import uuid4

import pytest
from notesolve.application.analysis import AnalysisService
from notesolve.domain.models import (
    LOCAL_WORKSPACE_ID,
    AnalyzeOptions,
    DocumentAnalysis,
    DocumentStatus,
    InputFile,
    PipelineStage,
    ProblemResult,
    VerificationResult,
    VerificationStatus,
    WorksheetResult,
)
from notesolve.infrastructure.db import Base
from notesolve.infrastructure.tables import DocumentRow, PipelineJobRow, WorksheetResultRow
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


class MemoryStorage:
    async def read(self, storage_key: str) -> bytes:
        return b"worksheet"


class LowConfidenceAnalyzer:
    provider_name = "test"
    model_name = "test-analyzer"
    prompt_version = "test-v1"

    async def analyze(
        self, files: list[InputFile], options: AnalyzeOptions
    ) -> WorksheetResult:
        return WorksheetResult(
            document=DocumentAnalysis(subject="math", confidence=0.8),
            problems=[ProblemResult(
                id="1",
                problem_type="short_answer",
                question_markdown="$x+1=4$",
                solution_markdown="$x=2$",
                answer_markdown="$x=2$",
                verification=VerificationResult(
                    status=VerificationStatus.SELF_CHECKED,
                    confidence=0.7,
                ),
                confidence=0.7,
            )],
        )


class ConflictVerifier:
    async def verify(
        self,
        files: list[InputFile],
        problem: ProblemResult,
        options: AnalyzeOptions,
    ) -> VerificationResult:
        return VerificationResult(
            status=VerificationStatus.CONFLICT,
            method="independent derivation",
            details_markdown="The correct answer is $x=3$.",
            confidence=0.99,
        )


@pytest.mark.asyncio
async def test_low_confidence_problem_is_flagged_when_independent_check_conflicts() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    document_id, job_id = uuid4(), uuid4()

    with session_factory() as session:
        session.add(DocumentRow(
            id=document_id,
            workspace_id=LOCAL_WORKSPACE_ID,
            original_filename="worksheet.png",
            content_type="image/png",
            storage_key="worksheet.png",
            content_hash="hash",
            size_bytes=9,
            status=DocumentStatus.INGESTED,
        ))
        session.add(PipelineJobRow(
            id=job_id,
            workspace_id=LOCAL_WORKSPACE_ID,
            document_id=document_id,
            stage=PipelineStage.INGESTED,
            progress=0,
        ))
        session.commit()
        service = AnalysisService(
            session=session,
            storage=MemoryStorage(),
            analyzer=LowConfidenceAnalyzer(),
            verifier=ConflictVerifier(),
        )
        await service.run(job_id)

        row = session.scalar(
            select(WorksheetResultRow).where(WorksheetResultRow.document_id == document_id)
        )
        assert row is not None
        problem = WorksheetResult.model_validate(row.result_json).problems[0]
        assert problem.verification.status == VerificationStatus.CONFLICT
        assert problem.needs_review is True
        assert "독립 검산" in problem.warnings[0]
        assert session.get(PipelineJobRow, job_id).stage == PipelineStage.COMPLETED
