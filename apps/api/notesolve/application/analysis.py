from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from notesolve.domain.models import AnalyzeOptions, DocumentStatus, InputFile, PipelineStage
from notesolve.domain.ports import StorageProvider, WorksheetAnalyzer
from notesolve.infrastructure.tables import DocumentRow, PipelineJobRow, WorksheetResultRow


class AnalysisService:
    def __init__(
        self,
        *,
        session: Session,
        storage: StorageProvider,
        analyzer: WorksheetAnalyzer,
    ) -> None:
        self._session = session
        self._storage = storage
        self._analyzer = analyzer

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
            result = await self._analyzer.analyze(
                [
                    InputFile(
                        storage_key=document.storage_key,
                        content_type=document.content_type,
                        original_filename=document.original_filename,
                        content=content,
                    )
                ],
                options or AnalyzeOptions(),
            )
            job.stage = PipelineStage.VALIDATING
            job.progress = 80
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
