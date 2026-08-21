from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from notesolve.domain.models import (
    AnalyzeOptions,
    DocumentStatus,
    InputFile,
    PipelineStage,
    VerificationStatus,
    WorksheetResult,
)
from notesolve.domain.ports import StorageProvider, WorksheetAnalyzer, WorksheetVerifier
from notesolve.infrastructure.tables import DocumentRow, PipelineJobRow, WorksheetResultRow


class AnalysisService:
    def __init__(
        self,
        *,
        session: Session,
        storage: StorageProvider,
        analyzer: WorksheetAnalyzer,
        verifier: WorksheetVerifier | None = None,
        verification_threshold: float = 0.9,
    ) -> None:
        self._session = session
        self._storage = storage
        self._analyzer = analyzer
        self._verifier = verifier
        self._verification_threshold = verification_threshold

    async def run(self, job_id: UUID, options: AnalyzeOptions | None = None) -> None:
        job = self._session.get(PipelineJobRow, job_id)
        if job is None:
            raise ValueError(f"Unknown analysis job: {job_id}")
        document = self._session.get(DocumentRow, job.document_id)
        if document is None:
            raise ValueError(f"Unknown document: {job.document_id}")
        existing = self._session.scalar(
            select(WorksheetResultRow).where(WorksheetResultRow.document_id == document.id)
        )
        if existing is not None:
            job.stage = PipelineStage.COMPLETED
            job.progress = 100
            self._session.commit()
            return

        job.stage = PipelineStage.ANALYZING
        job.progress = 10
        document.status = DocumentStatus.PROCESSING
        self._session.commit()
        try:
            content = await self._storage.read(document.storage_key)
            input_files = [
                InputFile(
                    storage_key=document.storage_key,
                    content_type=document.content_type,
                    original_filename=document.original_filename,
                    content=content,
                )
            ]
            analysis_options = options or AnalyzeOptions()
            result = await self._analyzer.analyze(input_files, analysis_options)
            job.stage = PipelineStage.VALIDATING
            job.progress = 70
            self._session.commit()
            result = await self._verify_low_confidence_problems(
                job=job,
                files=input_files,
                result=result,
                options=analysis_options,
            )
            self._session.add(
                WorksheetResultRow(
                    id=uuid4(),
                    workspace_id=document.workspace_id,
                    document_id=document.id,
                    job_id=job.id,
                    provider=getattr(self._analyzer, "provider_name", "unknown"),
                    model=getattr(self._analyzer, "model_name", "unknown"),
                    prompt_version=getattr(self._analyzer, "prompt_version", "unknown"),
                    result_json=result.model_dump(mode="json"),
                )
            )
            job.stage = PipelineStage.COMPLETED
            job.progress = 100
            document.status = DocumentStatus.COMPLETED
            self._session.commit()
        except Exception as exc:
            self._session.rollback()
            job = self._session.get(PipelineJobRow, job_id)
            document = self._session.get(DocumentRow, job.document_id) if job else None
            if job is not None:
                job.stage = PipelineStage.FAILED
                job.error_code = "analysis_failed"
                job.error_message = str(exc)[:1000]
            if document is not None:
                document.status = DocumentStatus.FAILED
            self._session.commit()
            raise

    async def _verify_low_confidence_problems(
        self,
        *,
        job: PipelineJobRow,
        files: list[InputFile],
        result: WorksheetResult,
        options: AnalyzeOptions,
    ) -> WorksheetResult:
        if self._verifier is None:
            return result
        candidates = [
            problem
            for problem in result.problems
            if problem.needs_review
            or problem.confidence < self._verification_threshold
            or problem.verification.confidence < self._verification_threshold
            or problem.verification.status
            in {
                VerificationStatus.CONFLICT,
                VerificationStatus.MANUAL_REVIEW_REQUIRED,
                VerificationStatus.UNSUPPORTED,
            }
        ]
        if not candidates:
            return result
        job.stage = PipelineStage.VERIFYING
        job.progress = 80
        self._session.commit()
        for problem in candidates:
            try:
                verification = await self._verifier.verify(files, problem, options)
            except Exception as exc:
                problem.verification.status = VerificationStatus.MANUAL_REVIEW_REQUIRED
                problem.verification.method = "independent_verification_failed"
                problem.verification.details_markdown = (
                    "독립 검산을 완료하지 못했습니다. 원래 풀이를 직접 검토해 주세요."
                )
                problem.verification.confidence = 0
                problem.needs_review = True
                warning = f"독립 검산 실패: {str(exc)[:200]}"
                if warning not in problem.warnings:
                    problem.warnings.append(warning)
                continue
            problem.verification = verification
            if verification.status in {
                VerificationStatus.CONFLICT,
                VerificationStatus.MANUAL_REVIEW_REQUIRED,
                VerificationStatus.UNSUPPORTED,
            }:
                problem.needs_review = True
                warning = "독립 검산에서 불일치 또는 수동 검토 필요 판정"
                if warning not in problem.warnings:
                    problem.warnings.append(warning)
        return result
