from uuid import UUID

from pydantic import BaseModel

from notesolve.domain.models import PipelineStage


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
