from uuid import UUID

from pydantic import BaseModel

from notesolve.domain.models import PipelineStage, VaultChangeSet, WorksheetResult


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class CreateDocumentResponse(BaseModel):
    document_id: UUID
    job_id: UUID
    status: str
    duplicate: bool


class JobStatusResponse(BaseModel):
    job_id: UUID
    document_id: UUID
    stage: PipelineStage
    progress: int
    error_code: str | None
    error_message: str | None


class AnalyzeJobResponse(BaseModel):
    job_id: UUID
    status: str


class WorksheetResultResponse(BaseModel):
    document_id: UUID
    job_id: UUID
    provider: str
    model: str
    prompt_version: str
    result: WorksheetResult


class VaultPreviewResponse(BaseModel):
    document_id: UUID
    change_set: VaultChangeSet
