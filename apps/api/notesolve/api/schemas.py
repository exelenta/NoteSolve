from uuid import UUID

from pydantic import BaseModel, Field

from notesolve.domain.models import (
    AgentEditJobStatus,
    PipelineStage,
    VaultChangeSet,
    VaultChangeSetStatus,
    WorksheetResult,
)


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


class VaultChangeSetResponse(BaseModel):
    document_id: UUID
    status: VaultChangeSetStatus
    error_message: str | None
    change_set: VaultChangeSet


class AgentEditRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=4000)


class AgentEditJobResponse(BaseModel):
    job_id: UUID
    status: AgentEditJobStatus
    result_change_set_id: UUID | None
    error_message: str | None
